"""
Network Monitor - Background monitoring for network connectivity
"""
import threading
import time
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Callable, Optional, List


class NetworkMonitor:
    """Background thread to monitor network connectivity"""

    def __init__(
        self,
        check_interval: int = 30,
        targets: Optional[List[str]] = None,
        failure_threshold: int = 3
    ):
        """
        Initialize NetworkMonitor

        Args:
            check_interval: Seconds between connectivity checks (default: 30)
            targets: List of IPs/hostnames to ping (default: ['8.8.8.8', '1.1.1.1'])
            failure_threshold: Consecutive failures before declaring network down (default: 3)
        """
        self.check_interval = check_interval
        self.targets = targets or ['8.8.8.8', '1.1.1.1']  # Google DNS and Cloudflare DNS
        self.failure_threshold = failure_threshold

        self.running = False
        self.thread = None
        self.is_online = True
        self.consecutive_failures = 0

        # Event callbacks
        self.on_network_down_callbacks: List[Callable] = []
        self.on_network_up_callbacks: List[Callable] = []

        # Logging
        self.log_file = Path.home() / 'backup-manager' / 'logs' / 'network_monitor.log'
        self.log_file.parent.mkdir(parents=True, exist_ok=True)

    def start(self):
        """Start the network monitor"""
        if self.running:
            return False

        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
        self.log("Network monitor started")
        return True

    def stop(self):
        """Stop the network monitor"""
        if not self.running:
            return False

        self.running = False
        if self.thread:
            self.thread.join(timeout=5)
        self.log("Network monitor stopped")
        return True

    def register_network_down_callback(self, callback: Callable):
        """
        Register a callback to be called when network goes down

        Args:
            callback: Function to call (takes no arguments)
        """
        self.on_network_down_callbacks.append(callback)

    def register_network_up_callback(self, callback: Callable):
        """
        Register a callback to be called when network comes back up

        Args:
            callback: Function to call (takes no arguments)
        """
        self.on_network_up_callbacks.append(callback)

    def get_status(self) -> dict:
        """
        Get current network status

        Returns:
            Dict with status information
        """
        return {
            'is_online': self.is_online,
            'consecutive_failures': self.consecutive_failures,
            'check_interval': self.check_interval,
            'targets': self.targets,
            'running': self.running
        }

    def _monitor_loop(self):
        """Main monitoring loop (runs in background thread)"""
        while self.running:
            try:
                # Check connectivity
                is_reachable = self._check_connectivity()

                if is_reachable:
                    # Network is up
                    if not self.is_online:
                        # Network just came back up
                        self.log("Network connectivity restored")
                        self.is_online = True
                        self._trigger_network_up_callbacks()

                    self.consecutive_failures = 0

                else:
                    # Network check failed
                    self.consecutive_failures += 1
                    self.log(f"Network check failed ({self.consecutive_failures}/{self.failure_threshold})")

                    if self.is_online and self.consecutive_failures >= self.failure_threshold:
                        # Network just went down
                        self.log("Network connectivity lost")
                        self.is_online = False
                        self._trigger_network_down_callbacks()

                # Sleep until next check
                time.sleep(self.check_interval)

            except Exception as e:
                self.log(f"Error in monitor loop: {e}")
                time.sleep(self.check_interval)

    def _check_connectivity(self) -> bool:
        """
        Check if network is reachable using socket connection to targets.
        Uses port 53 (DNS) for connectivity check - more portable than ping.

        Returns:
            True if at least one target is reachable
        """
        import socket

        for target in self.targets:
            try:
                # Try to connect to DNS port with 2 second timeout
                # This is more portable than ping and doesn't require root
                socket.create_connection((target, 53), timeout=2)
                return True

            except (socket.timeout, socket.error, OSError) as e:
                self.log(f"Cannot reach {target}: {e}")
                continue
            except Exception as e:
                self.log(f"Unexpected error checking {target}: {e}")
                continue

        return False

    def _trigger_network_down_callbacks(self):
        """Trigger all registered network down callbacks"""
        for callback in self.on_network_down_callbacks:
            try:
                callback()
            except Exception as e:
                self.log(f"Error in network down callback: {e}")

    def _trigger_network_up_callbacks(self):
        """Trigger all registered network up callbacks"""
        for callback in self.on_network_up_callbacks:
            try:
                callback()
            except Exception as e:
                self.log(f"Error in network up callback: {e}")

    def log(self, message: str):
        """Write to log file"""
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            with open(self.log_file, 'a') as f:
                f.write(f"[{timestamp}] {message}\n")
        except Exception:
            pass  # Don't let logging errors crash the monitor


# Global singleton instance
_network_monitor_instance = None


def get_network_monitor() -> NetworkMonitor:
    """Get the global NetworkMonitor singleton"""
    global _network_monitor_instance
    if _network_monitor_instance is None:
        _network_monitor_instance = NetworkMonitor()
    return _network_monitor_instance
