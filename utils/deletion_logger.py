"""
Deletion Logger - Audit trail for deleted source files

Provides comprehensive logging of all file deletions during backup operations
to ensure accountability and enable recovery planning.
"""
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
import os


class DeletionLogger:
    """Logs file deletions for audit and recovery purposes"""

    def __init__(self, job_id: str):
        """
        Initialize deletion logger for a specific job

        Args:
            job_id: UUID of the backup job
        """
        self.job_id = job_id
        self.log_dir = Path.home() / 'backup-manager' / 'logs'
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.log_file = self.log_dir / f'deletions_{job_id}.log'

    def log_deletion(self, file_path: str, file_size: int = 0, extra_info: str = "") -> bool:
        """
        Log a file deletion event

        Args:
            file_path: Absolute path of deleted file
            file_size: Size of file in bytes (0 if unknown)
            extra_info: Optional additional information

        Returns:
            True if logged successfully, False otherwise
        """
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # Format size
            if file_size > 1024**3:
                size_str = f"{file_size / 1024**3:.2f} GB"
            elif file_size > 1024**2:
                size_str = f"{file_size / 1024**2:.2f} MB"
            elif file_size > 1024:
                size_str = f"{file_size / 1024:.2f} KB"
            else:
                size_str = f"{file_size} B"

            # Build log entry
            log_entry = f"[{timestamp}] DELETED: {file_path} (size: {size_str})"
            if extra_info:
                log_entry += f" | {extra_info}"

            # Write to log file
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry + '\n')

            return True

        except Exception as e:
            # Don't crash on logging errors, but print warning
            print(f"Warning: Failed to log deletion: {e}")
            return False

    def log_deletion_start(self, mode: str, total_files: int = 0):
        """
        Log the start of a deletion operation

        Args:
            mode: Deletion mode ('verify_then_delete' or 'per_file')
            total_files: Estimated number of files to delete (0 if unknown)
        """
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            separator = "=" * 80

            log_entry = f"\n{separator}\n"
            log_entry += f"[{timestamp}] DELETION STARTED\n"
            log_entry += f"Mode: {mode}\n"
            if total_files > 0:
                log_entry += f"Estimated files: {total_files}\n"
            log_entry += f"Job ID: {self.job_id}\n"
            log_entry += f"{separator}\n"

            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry)

        except Exception as e:
            print(f"Warning: Failed to log deletion start: {e}")

    def log_deletion_complete(self, files_deleted: int, bytes_deleted: int, errors: int = 0):
        """
        Log the completion of a deletion operation

        Args:
            files_deleted: Number of files successfully deleted
            bytes_deleted: Total bytes deleted
            errors: Number of deletion errors encountered
        """
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            separator = "=" * 80

            # Format total size
            if bytes_deleted > 1024**3:
                total_size = f"{bytes_deleted / 1024**3:.2f} GB"
            elif bytes_deleted > 1024**2:
                total_size = f"{bytes_deleted / 1024**2:.2f} MB"
            elif bytes_deleted > 1024:
                total_size = f"{bytes_deleted / 1024:.2f} KB"
            else:
                total_size = f"{bytes_deleted} B"

            log_entry = f"\n{separator}\n"
            log_entry += f"[{timestamp}] DELETION COMPLETED\n"
            log_entry += f"Files deleted: {files_deleted}\n"
            log_entry += f"Total size freed: {total_size}\n"
            if errors > 0:
                log_entry += f"Errors: {errors}\n"
            log_entry += f"{separator}\n\n"

            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry)

        except Exception as e:
            print(f"Warning: Failed to log deletion complete: {e}")

    def log_verification_start(self):
        """Log the start of backup verification phase"""
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            log_entry = f"[{timestamp}] VERIFICATION STARTED - Checking backup integrity before deletion\n"

            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry)

        except Exception as e:
            print(f"Warning: Failed to log verification start: {e}")

    def log_verification_result(self, passed: bool, details: str = ""):
        """
        Log the result of backup verification

        Args:
            passed: True if verification passed, False otherwise
            details: Optional details about verification
        """
        try:
            timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            status = "PASSED" if passed else "FAILED"
            log_entry = f"[{timestamp}] VERIFICATION {status}"
            if details:
                log_entry += f" - {details}"
            log_entry += "\n"

            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(log_entry)

        except Exception as e:
            print(f"Warning: Failed to log verification result: {e}")

    def get_deletion_count(self) -> int:
        """
        Count total number of files deleted (from log file)

        Returns:
            Number of DELETED entries in log
        """
        try:
            if not self.log_file.exists():
                return 0

            count = 0
            with open(self.log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if ' DELETED: ' in line:
                        count += 1

            return count

        except Exception as e:
            print(f"Warning: Failed to count deletions: {e}")
            return 0

    def get_deletion_log(self, limit: int = 100) -> List[Dict]:
        """
        Retrieve deletion log entries

        Args:
            limit: Maximum number of entries to return (most recent first)

        Returns:
            List of deletion log dictionaries with keys:
            - timestamp: When file was deleted
            - file_path: Path of deleted file
            - size: File size
            - extra_info: Additional information
        """
        try:
            if not self.log_file.exists():
                return []

            entries = []

            with open(self.log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            # Parse DELETED entries (reverse order for most recent first)
            for line in reversed(lines):
                if ' DELETED: ' not in line:
                    continue

                try:
                    # Parse: [2025-01-15 10:30:45] DELETED: /path/to/file (size: 1.5 MB) | extra
                    parts = line.strip().split('] DELETED: ', 1)
                    if len(parts) != 2:
                        continue

                    timestamp = parts[0][1:]  # Remove leading [
                    rest = parts[1]

                    # Split path and metadata
                    if ' (size: ' in rest:
                        file_path, metadata = rest.split(' (size: ', 1)
                        metadata = metadata.rstrip(')')

                        # Extract size and extra info
                        if ' | ' in metadata:
                            size_str, extra_info = metadata.split(' | ', 1)
                        else:
                            size_str = metadata
                            extra_info = ""
                    else:
                        file_path = rest
                        size_str = "unknown"
                        extra_info = ""

                    entries.append({
                        'timestamp': timestamp,
                        'file_path': file_path,
                        'size': size_str,
                        'extra_info': extra_info
                    })

                    if len(entries) >= limit:
                        break

                except Exception:
                    # Skip malformed lines
                    continue

            return entries

        except Exception as e:
            print(f"Warning: Failed to read deletion log: {e}")
            return []

    def get_total_bytes_deleted(self) -> int:
        """
        Calculate total bytes deleted (estimated from log)

        Returns:
            Approximate total bytes deleted
        """
        try:
            entries = self.get_deletion_log(limit=10000)  # Get all entries
            total = 0

            for entry in entries:
                size_str = entry['size']
                if size_str == "unknown":
                    continue

                # Parse size string like "1.5 MB" or "512 KB"
                try:
                    parts = size_str.split()
                    if len(parts) == 2:
                        value = float(parts[0])
                        unit = parts[1].upper()

                        multipliers = {
                            'B': 1,
                            'KB': 1024,
                            'MB': 1024**2,
                            'GB': 1024**3,
                            'TB': 1024**4,
                        }

                        total += int(value * multipliers.get(unit, 1))
                except Exception:
                    continue

            return total

        except Exception as e:
            print(f"Warning: Failed to calculate total bytes deleted: {e}")
            return 0

    def exists(self) -> bool:
        """
        Check if deletion log file exists

        Returns:
            True if log file exists
        """
        return self.log_file.exists()

    def get_log_file_path(self) -> Path:
        """
        Get the path to the deletion log file

        Returns:
            Path object to log file
        """
        return self.log_file
