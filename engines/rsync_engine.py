"""
rsync Engine - Handles local and network file transfers
"""
import subprocess
import threading
import time
import re
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

    def __init__(self, source, dest, job_id, bandwidth_limit=None, max_retries=10):
        self.source = source
        self.dest = dest
        self.job_id = job_id
        self.bandwidth_limit = bandwidth_limit
        self.max_retries = max_retries
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
            'status': 'pending'
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
            self.running = True
            self.progress['status'] = 'running'

            # Start monitoring thread
            self.thread = threading.Thread(target=self._monitor_output, daemon=True)
            self.thread.start()

            return True
        except Exception as e:
            self.log(f"Error starting rsync: {e}")
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
            self.running = False
            self.progress['status'] = 'paused'
            self.log("rsync stopped by user")
            return True
        except Exception as e:
            self.log(f"Error stopping rsync: {e}")
            if self.process:
                self.process.kill()
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
                for line in self.process.stdout:
                    self.log(line.strip())
                    self._parse_progress(line)
                    output_buffer.append(line.lower())  # Collect for error checking

                # Process finished
                self.process.wait()
                returncode = self.process.returncode

                if returncode == 0:
                    # Success!
                    self.progress['status'] = 'completed'
                    self.progress['percent'] = 100
                    self.log("rsync completed successfully")
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
                        self.progress['status'] = 'running (retrying...)'

                        # Wait before retry
                        time.sleep(backoff)

                        # Restart rsync if still running flag is True
                        if self.running:
                            self.log(f"Retry attempt {self.retry_count}: Restarting rsync")
                            output_buffer.clear()  # Clear buffer for new attempt
                            if not self._restart_process():
                                self.log("Failed to restart rsync process")
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
                    # Note: stderr is merged into stdout, error output already logged
                    self.log(f"rsync failed with code {returncode}")
                    self.progress['status'] = 'failed'
                    self.running = False
                    break

            except Exception as e:
                self.log(f"Error monitoring rsync: {e}")
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
            # Format: to-chk=remaining/total (e.g., to-chk=1/2514 means 2513 done, 1 remaining)
            check_match = re.search(r'to-chk(?:eck)?=(\d+)/(\d+)', line)
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

    def log(self, message):
        """Write to log file"""
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            with open(self.log_file, 'a') as f:
                f.write(f"[{timestamp}] {message}\n")
        except Exception:
            pass  # Don't let logging errors crash the engine
