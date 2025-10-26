"""
rsync Engine - Handles local and network file transfers
"""
import subprocess
import threading
import time
import re
import os
from pathlib import Path
from datetime import datetime


class RsyncEngine:
    # Definite network-related rsync error codes (removed 23 - it's ambiguous)
    NETWORK_ERROR_CODES = [10, 12, 30, 35]  # Connection errors, timeouts, etc.

    # Network-related error patterns in rsync output (for code 23 disambiguation)
    NETWORK_ERROR_PATTERNS = [
        'connection refused',
        'connection reset',
        'connection timed out',
        'connection closed',
        'network is unreachable',
        'no route to host',
        'temporary failure',
        'timeout',
        'broken pipe',
        'connection unexpectedly closed'
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
        self.log_file = Path.home() / 'backup-manager' / 'logs' / f'rsync_{job_id}.log'
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

        # Check if --append-verify is supported (requires rsync 3.0+)
        self.supports_append_verify = self._check_append_verify_support()

    def start(self):
        """Start the rsync process"""
        if self.running:
            return False

        # Log deletion mode if enabled
        if self.delete_source_after:
            self.log(f"⚠️ DELETION MODE ENABLED: {self.deletion_mode}")
            if self.deletion_logger:
                from utils.safety_checks import count_files_in_directory
                total_files = count_files_in_directory(self.source)
                self.deletion_logger.log_deletion_start(self.deletion_mode, total_files)
            with self._progress_lock:
                self.progress['deletion']['phase'] = 'transfer'

        # Build rsync command with resume support
        cmd = [
            'rsync',
            '-ah',  # Archive mode, human-readable
            '--partial',  # Keep partially transferred files for resume
            '--progress'  # Show progress
        ]

        # Add --append-verify if supported (requires rsync 3.0+, not available on macOS 2.6.9)
        if self.supports_append_verify:
            cmd.append('--append-verify')

        # Handle deletion modes
        if self.delete_source_after and self.deletion_mode == 'per_file':
            # Per-file deletion: delete each file immediately after successful transfer
            cmd.append('--remove-source-files')
            self.log("Using per-file deletion (--remove-source-files)")

        # Add checksum verification based on verification mode
        if self.verification_mode == 'checksum':
            cmd.append('--checksum')  # Compare files using checksums, not just size/time
            self.log("Verification mode: checksum (slower but verified)")

        if self.bandwidth_limit:
            cmd.extend(['--bwlimit', f'{self.bandwidth_limit}k'])

        cmd.extend([self.source, self.dest])

        # Start process
        try:
            self.log(f"Starting rsync: {' '.join(cmd)}")
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # Merge stderr into stdout to prevent pipe deadlock
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
            self.log(f"Error starting rsync: {e}")
            with self._progress_lock:
                self.progress['status'] = 'failed'
            return False

    def stop(self):
        """Stop the rsync process"""
        if not self.running:
            return False

        try:
            if self.process:
                self.process.terminate()

                # Drain remaining output to capture final progress
                try:
                    # Read remaining lines with a short timeout
                    for _ in range(10):  # Read up to 10 lines
                        line = self.process.stdout.readline()
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
            self.log("rsync stopped by user")
            return True
        except Exception as e:
            self.log(f"Error stopping rsync: {e}")
            if self.process:
                self.process.kill()
            with self._progress_lock:
                self.running = False
            return True

    def is_running(self):
        """Check if rsync is currently running"""
        return self.running and self.process and self.process.poll() is None

    def get_progress(self):
        """Get current progress"""
        with self._progress_lock:
            return self.progress.copy()

    def _monitor_output(self):
        """Monitor rsync output in background thread with auto-retry"""
        output_buffer = []  # Collect output for error pattern matching

        while self.running:
            try:
                # Read output character by character to handle \r (carriage return) used by rsync --progress
                current_line = ""
                while True:
                    char = self.process.stdout.read(1)
                    if not char:
                        break  # EOF

                    if char == '\n':
                        # Newline - process complete line
                        if current_line:
                            self.log(current_line)
                            self._parse_progress(current_line)
                            output_buffer.append(current_line.lower())
                        current_line = ""
                    elif char == '\r':
                        # Carriage return - treat as line delimiter for progress updates
                        if current_line:
                            self._parse_progress(current_line)  # Parse but don't log yet (gets overwritten)
                        current_line = ""
                    else:
                        current_line += char

                # Process finished
                self.process.wait()
                returncode = self.process.returncode

                if returncode == 0:
                    # Success!
                    self.log("rsync completed successfully")

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

                    # Handle per_file deletion cleanup (remove empty dirs)
                    elif self.delete_source_after and self.deletion_mode == 'per_file':
                        self.log("Cleaning up empty directories after per-file deletion")
                        self._cleanup_empty_dirs(Path(self.source))

                        with self._progress_lock:
                            self.progress['deletion']['phase'] = 'completed'

                        # Log completion
                        if self.deletion_logger:
                            # Can't easily count files deleted by rsync --remove-source-files
                            # Estimate based on completion
                            self.deletion_logger.log_deletion_complete(0, 0, errors=0)

                    # Update completion status atomically (CRITICAL FIX)
                    with self._progress_lock:
                        self.progress['status'] = 'completed'
                        self.progress['percent'] = 100
                        self.running = False
                    break

                elif returncode in self.NETWORK_ERROR_CODES or self._is_network_error(returncode, output_buffer):
                    # Network error (definite code or pattern-matched) - attempt retry
                    self.log(f"rsync network error (code {returncode})")

                    if self.retry_count < self.max_retries:
                        # Calculate exponential backoff (1s, 2s, 4s, 8s, 16s, 32s, max 60s)
                        backoff = min(2 ** self.retry_count, 60)
                        self.retry_count += 1

                        self.log(f"Retrying in {backoff}s (attempt {self.retry_count}/{self.max_retries})...")
                        with self._progress_lock:
                            self.progress['status'] = 'running (retrying...)'

                        # Wait before retry
                        time.sleep(backoff)

                        # Restart rsync if still running flag is True
                        if self.running:
                            self.log(f"Retry attempt {self.retry_count}: Restarting rsync")
                            output_buffer.clear()  # Clear buffer for new attempt
                            if not self._restart_process():
                                self.log("Failed to restart rsync process")
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
                    # Note: stderr is merged into stdout, error output already logged
                    self.log(f"rsync failed with code {returncode}")
                    with self._progress_lock:
                        self.progress['status'] = 'failed'
                        self.running = False
                    break

            except Exception as e:
                self.log(f"Error monitoring rsync: {e}")
                with self._progress_lock:
                    self.progress['status'] = 'failed'
                    self.running = False
                break

    def _restart_process(self):
        """Restart the rsync process (for retry with resume)"""
        try:
            # Build rsync command with resume support (same as start())
            cmd = [
                'rsync',
                '-ah',
                '--partial',  # Resume from partial files
                '--progress'
            ]

            # Add --append-verify if supported
            if self.supports_append_verify:
                cmd.append('--append-verify')

            # Add checksum verification based on verification mode
            if self.verification_mode == 'checksum':
                cmd.append('--checksum')

            if self.bandwidth_limit:
                cmd.extend(['--bwlimit', f'{self.bandwidth_limit}k'])

            cmd.extend([self.source, self.dest])

            # Start new process
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # Merge stderr into stdout to prevent pipe deadlock
                universal_newlines=True,
                errors='replace',  # Replace invalid UTF-8 bytes instead of crashing
                bufsize=1
            )
            return True

        except Exception as e:
            self.log(f"Error restarting rsync: {e}")
            return False

    def _parse_progress(self, line):
        """Parse rsync progress output"""
        try:
            # rsync progress format: "  1,234,567,890  12%   2.34MB/s    0:01:23 (xfr#9, to-chk=123/456)"
            # or simpler: "  1,234,567,890  12%   2.34MB/s    0:01:23"

            updates = {}

            # Look for "to-check=X/Y" or "to-chk=X/Y" for overall progress
            # Format: to-check=remaining/total (e.g., to-check=1/2514 means 2513 done, 1 remaining)
            check_match = re.search(r'to-ch(?:ec)?k=(\d+)/(\d+)', line)
            if check_match:
                remaining = int(check_match.group(1))
                total = int(check_match.group(2))
                if total > 0:
                    completed = total - remaining
                    percent = int((completed / total) * 100)
                    updates['percent'] = percent

            # Look for transferred bytes (number with commas before the %)
            bytes_match = re.search(r'[\s,]+([\d,]+)[\s,]+\d+%', line)
            if bytes_match:
                bytes_str = bytes_match.group(1).replace(',', '')
                updates['bytes_transferred'] = int(bytes_str)

            # Calculate total_bytes from bytes_transferred and percent
            # Formula: total_bytes = bytes_transferred / (percent / 100)
            # Only calculate if we have both bytes and percent, and percent > 0
            if 'bytes_transferred' in updates and 'percent' in updates:
                percent = updates['percent']
                bytes_transferred = updates['bytes_transferred']
                if percent > 0:
                    # Calculate total, but only set if not already established
                    calculated_total = int(bytes_transferred / (percent / 100.0))
                    # Only update total_bytes if we don't have one yet, or if new calculation seems more accurate
                    with self._progress_lock:
                        current_total = self.progress.get('total_bytes', 0)
                        if current_total == 0 or abs(calculated_total - current_total) > current_total * 0.1:
                            # Either first calculation, or >10% different (likely more accurate)
                            updates['total_bytes'] = calculated_total

            # Look for speed (e.g., "2.34MB/s" or "123.45kB/s")
            speed_match = re.search(r'([\d.]+)(MB|KB|GB)/s', line, re.IGNORECASE)
            if speed_match:
                speed = float(speed_match.group(1))
                unit = speed_match.group(2).upper()
                multiplier = {'KB': 1024, 'MB': 1024*1024, 'GB': 1024*1024*1024}
                updates['speed_bytes'] = int(speed * multiplier.get(unit, 1))

            # Look for ETA (e.g., "0:01:23")
            eta_match = re.search(r'(\d+):(\d+):(\d+)', line)
            if eta_match:
                hours = int(eta_match.group(1))
                minutes = int(eta_match.group(2))
                seconds = int(eta_match.group(3))
                updates['eta_seconds'] = hours * 3600 + minutes * 60 + seconds

            # Apply all updates atomically with lock
            if updates:
                with self._progress_lock:
                    self.progress.update(updates)

        except Exception as e:
            # Parsing errors are non-fatal, just log them
            self.log(f"Progress parse error: {e}")

    def _is_network_error(self, returncode, output_buffer):
        """
        Check if error is network-related by examining output patterns.
        Used for ambiguous error codes like 23 (partial transfer).

        Args:
            returncode: rsync exit code
            output_buffer: list of output lines (lowercased)

        Returns:
            True if network error patterns detected
        """
        # Only check patterns for ambiguous codes (like 23)
        if returncode not in [23]:
            return False

        # Check last 50 lines for network error patterns
        recent_output = ''.join(output_buffer[-50:])
        return any(pattern in recent_output for pattern in self.NETWORK_ERROR_PATTERNS)

    def _check_append_verify_support(self):
        """
        Check if rsync supports --append-verify flag (requires version 3.0+).
        macOS typically ships with rsync 2.6.9 which doesn't support it.

        Returns:
            True if --append-verify is supported
        """
        try:
            # Try running rsync with --help and check for append-verify
            result = subprocess.run(
                ['rsync', '--help'],
                capture_output=True,
                text=True,
                timeout=5
            )
            return '--append-verify' in result.stdout or '--append-verify' in result.stderr
        except Exception:
            # If we can't determine, assume not supported (safe default)
            return False

    def _verify_backup(self) -> bool:
        """
        Verify backup integrity before deletion (Phase 1 of verify_then_delete)

        Uses rsync --dry-run --checksum to compare source and destination

        Returns:
            True if verification passed, False otherwise
        """
        try:
            self.log("Starting backup verification with checksums...")
            if self.deletion_logger:
                self.deletion_logger.log_verification_start()

            # Build verification command
            cmd = [
                'rsync',
                '--dry-run',  # Don't actually transfer, just check
                '--checksum',  # Use checksums for comparison
                '-r',  # Recursive
                '-i',  # Item-ize changes (shows what would be transferred)
                self.source,
                self.dest
            ]

            # Run verification (no timeout - verification can take as long as needed)
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True
            )

            # Parse output - if there are files that would be transferred, verification failed
            output = result.stdout
            changes = [line for line in output.splitlines() if line.startswith('>')]

            if changes:
                # Files differ between source and destination
                self.log(f"❌ Verification failed: {len(changes)} file(s) differ")
                if self.deletion_logger:
                    self.deletion_logger.log_verification_result(False, f"{len(changes)} mismatches found")
                return False

            # All files match
            self.log("✅ Verification passed: all files match")
            if self.deletion_logger:
                self.deletion_logger.log_verification_result(True, "All files verified")
            return True

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

        Walks the source directory and deletes all files, logging each deletion

        Returns:
            True if deletion succeeded, False if errors occurred
        """
        try:
            source_path = Path(self.source)
            if not source_path.exists():
                self.log("Source path no longer exists - nothing to delete")
                return True

            files_deleted = 0
            bytes_deleted = 0
            errors = 0

            # Walk directory tree and delete files
            if source_path.is_file():
                # Single file source
                files_to_delete = [source_path]
            else:
                # Directory source - get all files
                files_to_delete = list(source_path.rglob('*'))
                files_to_delete = [f for f in files_to_delete if f.is_file()]

            total_files = len(files_to_delete)
            self.log(f"Deleting {total_files} file(s) from source...")

            for file_path in files_to_delete:
                try:
                    # Get file size before deletion
                    file_size = file_path.stat().st_size

                    # Delete the file
                    file_path.unlink()

                    # Log deletion
                    if self.deletion_logger:
                        self.deletion_logger.log_deletion(str(file_path), file_size)

                    files_deleted += 1
                    bytes_deleted += file_size

                    # Update progress
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
            if not directory.exists() or not directory.is_dir():
                return

            self.log(f"Cleaning up empty directories in {directory}...")

            # Walk from bottom up (deepest first)
            for dirpath in sorted(directory.rglob('*'), reverse=True):
                if dirpath.is_dir():
                    try:
                        # Try to remove if empty
                        dirpath.rmdir()
                        self.log(f"Removed empty directory: {dirpath}")
                    except OSError:
                        # Directory not empty or permission denied - skip
                        pass

            # Try to remove root directory if it's now empty
            try:
                if directory != Path(self.source):  # Don't remove if it's the original source
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
