"""
rclone Engine - Handles cloud storage transfers via rclone
"""
import subprocess
import threading
import time
import re
import os
from pathlib import Path
from datetime import datetime


class RcloneEngine:
    """Manages rclone transfers for cloud storage backups"""

    # Network-related error patterns in rclone stderr
    NETWORK_ERROR_PATTERNS = [
        'connection refused',
        'connection reset',
        'connection timed out',
        'network is unreachable',
        'no route to host',
        'temporary failure',
        'timeout',
        'too many open files'
    ]

    def __init__(self, source, dest, job_id, bandwidth_limit=None, max_retries=10,
                 verification_mode='fast', delete_source_after=False, deletion_mode='verify_then_delete',
                 deletion_logger=None):
        self.source = source
        self.dest = dest
        self.job_id = job_id
        self.bandwidth_limit = bandwidth_limit
        self.max_retries = max_retries
        self.verification_mode = verification_mode  # 'fast', 'checksum', or 'verify_after'
        self.delete_source_after = delete_source_after
        self.deletion_mode = deletion_mode  # 'verify_then_delete' or 'per_file'
        self.deletion_logger = deletion_logger  # DeletionLogger instance
        self.retry_count = 0
        self.process = None
        self.thread = None
        self.running = False
        self.progress = {
            'bytes_transferred': 0,
            'total_bytes': 0,
            'percent': 0,
            'speed_bytes': 0,
            'eta_seconds': 0,
            'status': 'pending',
            'verification': {
                'enabled': verification_mode != 'fast',
                'passed': None,
                'files_checked': 0,
                'mismatches': 0
            },
            'deletion': {
                'enabled': delete_source_after,
                'mode': deletion_mode,
                'phase': 'none',  # 'none', 'transfer', 'verifying', 'deleting', 'completed'
                'files_deleted': 0,
                'bytes_deleted': 0
            }
        }
        self._progress_lock = threading.Lock()  # Protect progress dict access

        # Use unified data directory for logs
        from core.paths import get_logs_dir
        self.log_file = get_logs_dir() / f'rclone_{job_id}.log'

    def start(self):
        """Start the rclone process"""
        if self.running:
            return False

        # Log deletion mode if enabled
        if self.delete_source_after:
            self.log(f"⚠️ DELETION MODE ENABLED: {self.deletion_mode}")
            if self.deletion_logger:
                from utils.safety_checks import count_files_in_directory
                # Try to count files, but source might be remote
                try:
                    total_files = count_files_in_directory(self.source)
                except:
                    total_files = 0  # Can't count remote files
                self.deletion_logger.log_deletion_start(self.deletion_mode, total_files)
            with self._progress_lock:
                self.progress['deletion']['phase'] = 'transfer'

        # Build rclone command
        # For per_file mode, use 'move' instead of 'copy'
        if self.delete_source_after and self.deletion_mode == 'per_file':
            operation = 'move'
            self.log("Using rclone move for per-file deletion")
        else:
            operation = 'copy'

        cmd = [
            'rclone', operation,
            '--progress',
            '--stats', '1s',  # Update stats every second
            '--stats-one-line',  # Compact stats output
            '--retries', '1',  # Let our wrapper handle retries
            '--low-level-retries', '3',  # But allow some low-level retries
        ]

        # Add --delete-empty-src-dirs for move operations
        if operation == 'move':
            cmd.append('--delete-empty-src-dirs')

        # Add checksum verification based on verification mode
        if self.verification_mode == 'checksum':
            cmd.append('--checksum')  # Use checksums for comparison, not just size/time
            self.log("Verification mode: checksum (slower but verified)")

        if self.bandwidth_limit:
            # rclone uses different format: --bwlimit 1M or --bwlimit 1000k
            cmd.extend(['--bwlimit', f'{self.bandwidth_limit}k'])

        cmd.extend([self.source, self.dest])

        # Start process
        try:
            self.log(f"Starting rclone: {' '.join(cmd)}")
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,  # Don't read stdout - prevents pipe deadlock
                stderr=subprocess.PIPE,     # Read stderr where rclone outputs stats
                universal_newlines=True,
                errors='replace',  # Replace invalid UTF-8 bytes instead of crashing
                bufsize=1
            )
            with self._progress_lock:
                self.running = True
                self.progress['status'] = 'running'

            # Start monitoring thread
            self.thread = threading.Thread(target=self._monitor_output, daemon=True)
            self.thread.start()

            return True
        except Exception as e:
            self.log(f"Error starting rclone: {e}")
            with self._progress_lock:
                self.progress['status'] = 'failed'
            return False

    def stop(self):
        """Stop the rclone process"""
        if not self.running:
            return False

        try:
            if self.process:
                self.process.terminate()

                # Drain remaining output to capture final progress
                try:
                    # Read remaining lines from stderr (where rclone outputs stats)
                    for _ in range(10):  # Read up to 10 lines
                        line = self.process.stderr.readline()
                        if not line:
                            break
                        self._parse_progress(line)
                        self.log(line.strip())
                except Exception:
                    pass  # Non-fatal if drain fails

                self.process.wait(timeout=5)
            with self._progress_lock:
                self.running = False
                self.progress['status'] = 'paused'
            self.log("rclone stopped by user")
            return True
        except Exception as e:
            self.log(f"Error stopping rclone: {e}")
            if self.process:
                self.process.kill()
            with self._progress_lock:
                self.running = False
            return True

    def is_running(self):
        """Check if rclone is currently running"""
        return self.running and self.process and self.process.poll() is None

    def get_progress(self):
        """Get current progress"""
        with self._progress_lock:
            return self.progress.copy()

    def _monitor_output(self):
        """Monitor rclone output in background thread with auto-retry"""
        stderr_buffer = []

        while self.running:
            try:
                # rclone outputs stats to stderr
                for line in self.process.stderr:
                    self.log(line.strip())
                    self._parse_progress(line)
                    stderr_buffer.append(line.lower())  # Collect for error checking

                # Process finished
                self.process.wait()
                returncode = self.process.returncode

                if returncode == 0:
                    # Success!
                    self.log("rclone completed successfully")

                    # Handle verify_then_delete mode
                    if self.delete_source_after and self.deletion_mode == 'verify_then_delete':
                        self.log("Starting verify-then-delete phase")

                        # Phase 1: Verify backup integrity
                        with self._progress_lock:
                            self.progress['deletion']['phase'] = 'verifying'

                        verification_passed = self._verify_backup()

                        if verification_passed:
                            self.log("✅ Verification passed - proceeding with deletion")

                            # Phase 2: Delete source files
                            with self._progress_lock:
                                self.progress['deletion']['phase'] = 'deleting'

                            deletion_success = self._delete_verified_files()

                            if deletion_success:
                                # Phase 3: Cleanup empty directories
                                self._cleanup_empty_dirs(Path(self.source))

                                with self._progress_lock:
                                    self.progress['deletion']['phase'] = 'completed'
                                self.log("✅ Deletion completed successfully")

                                # Log final stats
                                if self.deletion_logger:
                                    files_deleted = self.progress['deletion']['files_deleted']
                                    bytes_deleted = self.progress['deletion']['bytes_deleted']
                                    self.deletion_logger.log_deletion_complete(files_deleted, bytes_deleted)
                            else:
                                self.log("❌ Deletion failed - some files may remain")
                        else:
                            self.log("❌ Verification failed - skipping deletion to preserve data integrity")
                            with self._progress_lock:
                                self.progress['deletion']['phase'] = 'failed'

                    # Handle per_file deletion (move operation) - already done by rclone move
                    elif self.delete_source_after and self.deletion_mode == 'per_file':
                        self.log("Per-file deletion completed by rclone move")

                        with self._progress_lock:
                            self.progress['deletion']['phase'] = 'completed'

                        # Log completion
                        if self.deletion_logger:
                            # Can't easily count files deleted by rclone move
                            self.deletion_logger.log_deletion_complete(0, 0, errors=0)

                    # Handle verify_after mode (independent of deletion)
                    # Only run if NOT already verified in verify_then_delete mode
                    if self.verification_mode == 'verify_after' and not (self.delete_source_after and self.deletion_mode == 'verify_then_delete'):
                        self.log("Running post-transfer verification (verify_after mode)...")
                        with self._progress_lock:
                            self.progress['verification']['passed'] = None  # Pending

                        verification_passed = self._verify_backup()

                        with self._progress_lock:
                            self.progress['verification']['passed'] = verification_passed

                        if verification_passed:
                            self.log("✅ Post-transfer verification passed")
                        else:
                            self.log("❌ Post-transfer verification failed")

                    # Update completion status atomically (CRITICAL FIX)
                    with self._progress_lock:
                        self.progress['status'] = 'completed'
                        self.progress['percent'] = 100
                        self.running = False
                    break

                else:
                    # Check if error is network-related
                    stderr_text = ''.join(stderr_buffer[-50:])  # Check last 50 lines
                    is_network_error = any(
                        pattern in stderr_text
                        for pattern in self.NETWORK_ERROR_PATTERNS
                    )

                    if is_network_error:
                        # Network error - attempt retry
                        self.log(f"rclone network error (code {returncode})")

                        if self.retry_count < self.max_retries:
                            # Calculate exponential backoff
                            backoff = min(2 ** self.retry_count, 60)
                            self.retry_count += 1

                            self.log(f"Retrying in {backoff}s (attempt {self.retry_count}/{self.max_retries})...")
                            with self._progress_lock:
                                self.progress['status'] = 'running (retrying...)'

                            # Wait before retry
                            time.sleep(backoff)

                            # Restart rclone if still running
                            if self.running:
                                self.log(f"Retry attempt {self.retry_count}: Restarting rclone")
                                stderr_buffer.clear()  # Clear buffer for new attempt
                                if not self._restart_process():
                                    self.log("Failed to restart rclone process")
                                    with self._progress_lock:
                                        self.progress['status'] = 'failed'
                                        self.running = False
                                    break
                                # Continue monitoring the new process
                                continue
                        else:
                            # Max retries exceeded
                            self.log(f"Max retries ({self.max_retries}) exceeded, giving up")
                            with self._progress_lock:
                                self.progress['status'] = 'failed'
                                self.running = False
                            break

                    else:
                        # Other error (not network-related)
                        self.log(f"rclone failed with code {returncode}")
                        with self._progress_lock:
                            self.progress['status'] = 'failed'
                            self.running = False
                        break

            except Exception as e:
                self.log(f"Error monitoring rclone: {e}")
                with self._progress_lock:
                    self.progress['status'] = 'failed'
                    self.running = False
                break

    def _restart_process(self):
        """Restart the rclone process (for retry with resume)"""
        try:
            # Determine operation type based on deletion settings (matching start() logic)
            if self.delete_source_after and self.deletion_mode == 'per_file':
                operation = 'move'
                self.log("Retry using rclone move for per-file deletion")
            else:
                operation = 'copy'

            # Build rclone command with resume support (same as start())
            cmd = [
                'rclone', operation,
                '--progress',
                '--stats', '1s',
                '--stats-one-line',
                '--retries', '1',  # Our wrapper handles retries
                '--low-level-retries', '3',
            ]

            # Add --delete-empty-src-dirs for move operations
            if operation == 'move':
                cmd.append('--delete-empty-src-dirs')

            # Add checksum verification based on verification mode
            if self.verification_mode == 'checksum':
                cmd.append('--checksum')

            if self.bandwidth_limit:
                cmd.extend(['--bwlimit', f'{self.bandwidth_limit}k'])

            cmd.extend([self.source, self.dest])

            # Start new process
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,  # Don't read stdout - prevents pipe deadlock
                stderr=subprocess.PIPE,     # Read stderr where rclone outputs stats
                universal_newlines=True,
                errors='replace',  # Replace invalid UTF-8 bytes instead of crashing
                bufsize=1
            )
            return True

        except Exception as e:
            self.log(f"Error restarting rclone: {e}")
            return False

    def _parse_progress(self, line):
        """
        Parse rclone progress output

        Example rclone output:
        Transferred:   	    1.234 MiB / 10.234 MiB, 12%, 2.456 MiB/s, ETA 3s
        """
        try:
            # Look for "Transferred:" line
            if 'Transferred:' not in line:
                return

            # Parse: "Transferred:   1.234 MiB / 10.234 MiB, 12%, 2.456 MiB/s, ETA 3s"
            updates = {}

            # Extract bytes transferred
            transferred_match = re.search(r'Transferred:\s+[\d.]+\s*(\w+)\s*/\s*([\d.]+\s*\w+),\s*(\d+)%', line)
            if transferred_match:
                # Parse percentage
                percent = int(transferred_match.group(3))
                updates['percent'] = percent

                # Parse transferred and total
                transferred_str = line.split('/')[0].split(':')[1].strip()
                total_str = line.split('/')[1].split(',')[0].strip()

                updates['bytes_transferred'] = self._parse_size(transferred_str)
                updates['total_bytes'] = self._parse_size(total_str)

            # Parse speed (e.g., "2.456 MiB/s")
            speed_match = re.search(r'([\d.]+)\s*(\w+)/s', line)
            if speed_match:
                speed_value = float(speed_match.group(1))
                speed_unit = speed_match.group(2)
                updates['speed_bytes'] = self._parse_size(f"{speed_value} {speed_unit}")

            # Parse ETA (e.g., "ETA 3s" or "ETA 1m30s" or "ETA 1h2m")
            eta_match = re.search(r'ETA\s+(\d+h)?(\d+m)?(\d+s)?', line)
            if eta_match:
                hours = int(eta_match.group(1)[:-1]) if eta_match.group(1) else 0
                minutes = int(eta_match.group(2)[:-1]) if eta_match.group(2) else 0
                seconds = int(eta_match.group(3)[:-1]) if eta_match.group(3) else 0
                updates['eta_seconds'] = hours * 3600 + minutes * 60 + seconds

            # Apply all updates atomically with lock
            if updates:
                with self._progress_lock:
                    self.progress.update(updates)

        except Exception as e:
            # Parsing errors are non-fatal, just log them
            self.log(f"Progress parse error: {e}")

    def _parse_size(self, size_str):
        """
        Parse size string to bytes

        Args:
            size_str: String like "1.234 MiB" or "10 GiB"

        Returns:
            Size in bytes
        """
        try:
            parts = size_str.strip().split()
            if len(parts) != 2:
                return 0

            value = float(parts[0])
            unit = parts[1].upper()

            # rclone uses binary units (KiB, MiB, GiB, TiB)
            multipliers = {
                'B': 1,
                'KIB': 1024,
                'MIB': 1024 ** 2,
                'GIB': 1024 ** 3,
                'TIB': 1024 ** 4,
                # Also handle metric units
                'KB': 1000,
                'MB': 1000 ** 2,
                'GB': 1000 ** 3,
                'TB': 1000 ** 4,
            }

            return int(value * multipliers.get(unit, 1))

        except Exception as e:
            self.log(f"Size parse error: {e}")
            return 0

    def _verify_backup(self) -> bool:
        """
        Verify backup integrity before deletion (Phase 1 of verify_then_delete)

        Uses rclone check to compare source and destination

        Returns:
            True if verification passed, False otherwise
        """
        try:
            self.log("Starting backup verification with rclone check...")
            if self.deletion_logger:
                self.deletion_logger.log_verification_start()

            # Build verification command
            cmd = [
                'rclone', 'check',
                self.source,
                self.dest
            ]

            # Add --checksum if verification mode is checksum
            if self.verification_mode == 'checksum':
                cmd.append('--checksum')

            # Run verification (no timeout - verification can take as long as needed)
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True
            )

            # rclone check returns 0 if files match, non-zero if differences found
            if result.returncode == 0:
                self.log("✅ Verification passed: all files match")
                if self.deletion_logger:
                    self.deletion_logger.log_verification_result(True, "All files verified")
                return True
            else:
                # Parse output to see what failed
                errors = result.stderr if result.stderr else result.stdout
                self.log(f"❌ Verification failed: differences found")
                self.log(f"Details: {errors[:200]}")  # Log first 200 chars
                if self.deletion_logger:
                    self.deletion_logger.log_verification_result(False, "Differences found")
                return False

        except subprocess.TimeoutExpired:
            self.log("❌ Verification timeout - backup too large or slow")
            if self.deletion_logger:
                self.deletion_logger.log_verification_result(False, "Timeout")
            return False
        except Exception as e:
            self.log(f"❌ Verification error: {e}")
            if self.deletion_logger:
                self.deletion_logger.log_verification_result(False, str(e))
            return False

    def _delete_verified_files(self) -> bool:
        """
        Delete source files after verification (Phase 2 of verify_then_delete)

        Walks the source directory and deletes all files (or uses rclone delete for remote)

        Returns:
            True if deletion succeeded, False if errors occurred
        """
        try:
            # Check if source is remote (contains ':')
            from utils.safety_checks import is_cloud_path

            if is_cloud_path(self.source):
                # Remote source - use rclone delete
                self.log(f"Deleting remote files from {self.source}...")
                cmd = ['rclone', 'delete', self.source, '--verbose']

                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=600  # 10 minute timeout
                )

                if result.returncode == 0:
                    self.log("✅ Remote files deleted successfully")

                    # Remove empty directories from remote
                    self.log("Removing empty directories from remote...")
                    rmdirs_cmd = ['rclone', 'rmdirs', self.source]
                    try:
                        rmdirs_result = subprocess.run(
                            rmdirs_cmd,
                            capture_output=True,
                            text=True,
                            timeout=60  # 1 minute timeout for rmdirs
                        )

                        if rmdirs_result.returncode == 0:
                            self.log("✅ Empty directories removed")
                        else:
                            # Don't fail the job if rmdirs fails
                            self.log(f"⚠️ Could not remove empty directories: {rmdirs_result.stderr}")
                    except subprocess.TimeoutExpired:
                        self.log("⚠️ Timeout removing empty directories (non-fatal)")
                    except Exception as e:
                        self.log(f"⚠️ Error removing empty directories: {e} (non-fatal)")

                    if self.deletion_logger:
                        # Can't easily count remote files
                        self.deletion_logger.log_deletion_complete(0, 0, errors=0)
                    return True
                else:
                    self.log(f"❌ Remote deletion failed: {result.stderr}")
                    return False

            else:
                # Local source - delete files manually (same as rsync)
                source_path = Path(self.source)
                if not source_path.exists():
                    self.log("Source path no longer exists - nothing to delete")
                    return True

                files_deleted = 0
                bytes_deleted = 0
                errors = 0

                # Walk directory tree and delete files
                if source_path.is_file():
                    files_to_delete = [source_path]
                else:
                    files_to_delete = list(source_path.rglob('*'))
                    files_to_delete = [f for f in files_to_delete if f.is_file()]

                total_files = len(files_to_delete)
                self.log(f"Deleting {total_files} file(s) from source...")

                for file_path in files_to_delete:
                    try:
                        file_size = file_path.stat().st_size
                        file_path.unlink()

                        if self.deletion_logger:
                            self.deletion_logger.log_deletion(str(file_path), file_size)

                        files_deleted += 1
                        bytes_deleted += file_size

                        with self._progress_lock:
                            self.progress['deletion']['files_deleted'] = files_deleted
                            self.progress['deletion']['bytes_deleted'] = bytes_deleted

                    except PermissionError:
                        self.log(f"Permission denied: {file_path}")
                        errors += 1
                    except Exception as e:
                        self.log(f"Error deleting {file_path}: {e}")
                        errors += 1

                self.log(f"Deleted {files_deleted} file(s), {bytes_deleted} bytes")
                if errors > 0:
                    self.log(f"⚠️ {errors} error(s) occurred during deletion")

                return errors == 0

        except Exception as e:
            self.log(f"❌ Fatal error during deletion: {e}")
            return False

    def _cleanup_empty_dirs(self, directory: Path):
        """
        Remove empty directories after file deletion (Phase 3)

        Args:
            directory: Root directory to clean up
        """
        try:
            from utils.safety_checks import is_cloud_path

            # Can't clean up remote directories easily
            if is_cloud_path(str(directory)):
                self.log("Skipping directory cleanup for remote source")
                return

            if not directory.exists() or not directory.is_dir():
                return

            self.log(f"Cleaning up empty directories in {directory}...")

            # Walk from bottom up (deepest first)
            for dirpath in sorted(directory.rglob('*'), reverse=True):
                if dirpath.is_dir():
                    try:
                        dirpath.rmdir()
                        self.log(f"Removed empty directory: {dirpath}")
                    except OSError:
                        pass  # Not empty or permission denied

            # Try to remove root directory if it's now empty
            try:
                if directory != Path(self.source):
                    directory.rmdir()
                    self.log(f"Removed empty root directory: {directory}")
            except OSError:
                pass  # Not empty or permission denied

        except Exception as e:
            self.log(f"Error during directory cleanup: {e}")

    def log(self, message):
        """Write to log file"""
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            with open(self.log_file, 'a') as f:
                f.write(f"[{timestamp}] {message}\n")
        except Exception:
            pass  # Don't let logging errors crash the engine
