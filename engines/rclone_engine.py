"""
rclone Engine - Handles cloud storage transfers via rclone
"""
import subprocess
import threading
import time
import re
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

    def __init__(self, source, dest, job_id, bandwidth_limit=None, max_retries=10, verification_mode='fast'):
        self.source = source
        self.dest = dest
        self.job_id = job_id
        self.bandwidth_limit = bandwidth_limit
        self.max_retries = max_retries
        self.verification_mode = verification_mode  # 'fast', 'checksum', or 'verify_after'
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
            }
        }
        self._progress_lock = threading.Lock()  # Protect progress dict access
        self.log_file = Path.home() / 'backup-manager' / 'logs' / f'rclone_{job_id}.log'
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

    def start(self):
        """Start the rclone process"""
        if self.running:
            return False

        # Build rclone command with resume support
        # Using 'copy' for one-way sync (automatically resumes/skips existing files)
        cmd = [
            'rclone', 'copy',
            '--progress',
            '--stats', '1s',  # Update stats every second
            '--stats-one-line',  # Compact stats output
            '--retries', '1',  # Let our wrapper handle retries
            '--low-level-retries', '3',  # But allow some low-level retries
        ]

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
            self.running = True
            self.progress['status'] = 'running'

            # Start monitoring thread
            self.thread = threading.Thread(target=self._monitor_output, daemon=True)
            self.thread.start()

            return True
        except Exception as e:
            self.log(f"Error starting rclone: {e}")
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
            self.running = False
            self.progress['status'] = 'paused'
            self.log("rclone stopped by user")
            return True
        except Exception as e:
            self.log(f"Error stopping rclone: {e}")
            if self.process:
                self.process.kill()
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
                    self.progress['status'] = 'completed'
                    self.progress['percent'] = 100
                    self.log("rclone completed successfully")
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
                            self.progress['status'] = 'running (retrying...)'

                            # Wait before retry
                            time.sleep(backoff)

                            # Restart rclone if still running
                            if self.running:
                                self.log(f"Retry attempt {self.retry_count}: Restarting rclone")
                                stderr_buffer.clear()  # Clear buffer for new attempt
                                if not self._restart_process():
                                    self.log("Failed to restart rclone process")
                                    self.progress['status'] = 'failed'
                                    self.running = False
                                    break
                                # Continue monitoring the new process
                                continue
                        else:
                            # Max retries exceeded
                            self.log(f"Max retries ({self.max_retries}) exceeded, giving up")
                            self.progress['status'] = 'failed'
                            self.running = False
                            break

                    else:
                        # Other error (not network-related)
                        self.log(f"rclone failed with code {returncode}")
                        self.progress['status'] = 'failed'
                        self.running = False
                        break

            except Exception as e:
                self.log(f"Error monitoring rclone: {e}")
                self.progress['status'] = 'failed'
                self.running = False
                break

    def _restart_process(self):
        """Restart the rclone process (for retry with resume)"""
        try:
            # Build rclone command with resume support (same as start())
            cmd = [
                'rclone', 'copy',
                '--progress',
                '--stats', '1s',
                '--stats-one-line',
                '--retries', '1',  # Our wrapper handles retries
                '--low-level-retries', '3',
            ]

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

    def log(self, message):
        """Write to log file"""
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            with open(self.log_file, 'a') as f:
                f.write(f"[{timestamp}] {message}\n")
        except Exception:
            pass  # Don't let logging errors crash the engine
