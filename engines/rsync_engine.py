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
    # Network-related rsync error codes
    NETWORK_ERROR_CODES = [10, 12, 23, 30, 35]  # Connection errors, I/O errors, etc.

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
        self.log_file = Path.home() / 'backup-manager' / 'logs' / f'rsync_{job_id}.log'
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

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
        return self.progress.copy()

    def _monitor_output(self):
        """Monitor rsync output in background thread with auto-retry"""
        while self.running:
            try:
                for line in self.process.stdout:
                    self.log(line.strip())
                    self._parse_progress(line)

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

                elif returncode in self.NETWORK_ERROR_CODES:
                    # Network error - attempt retry
                    # Note: stderr is merged into stdout, error output already logged
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

            # Look for "to-check=X/Y" or "to-chk=X/Y" for overall progress
            # Format: to-chk=remaining/total (e.g., to-chk=1/2514 means 2513 done, 1 remaining)
            check_match = re.search(r'to-chk(?:eck)?=(\d+)/(\d+)', line)
            if check_match:
                remaining = int(check_match.group(1))
                total = int(check_match.group(2))
                if total > 0:
                    completed = total - remaining
                    percent = int((completed / total) * 100)
                    self.progress['percent'] = percent

            # Look for transferred bytes (number with commas before the %)
            bytes_match = re.search(r'[\s,]+([\d,]+)[\s,]+\d+%', line)
            if bytes_match:
                bytes_str = bytes_match.group(1).replace(',', '')
                self.progress['bytes_transferred'] = int(bytes_str)

            # Look for speed (e.g., "2.34MB/s" or "123.45kB/s")
            speed_match = re.search(r'([\d.]+)(MB|KB|GB)/s', line, re.IGNORECASE)
            if speed_match:
                speed = float(speed_match.group(1))
                unit = speed_match.group(2).upper()
                multiplier = {'KB': 1024, 'MB': 1024*1024, 'GB': 1024*1024*1024}
                self.progress['speed_bytes'] = int(speed * multiplier.get(unit, 1))

            # Look for ETA (e.g., "0:01:23")
            eta_match = re.search(r'(\d+):(\d+):(\d+)', line)
            if eta_match:
                hours = int(eta_match.group(1))
                minutes = int(eta_match.group(2))
                seconds = int(eta_match.group(3))
                self.progress['eta_seconds'] = hours * 3600 + minutes * 60 + seconds

        except Exception as e:
            # Parsing errors are non-fatal, just log them
            self.log(f"Progress parse error: {e}")

    def log(self, message):
        """Write to log file"""
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            with open(self.log_file, 'a') as f:
                f.write(f"[{timestamp}] {message}\n")
        except Exception:
            pass  # Don't let logging errors crash the engine
