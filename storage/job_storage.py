"""
Job storage manager - YAML-based persistence for backup jobs
"""
import yaml
import fcntl
import shutil
import queue
import threading
import atexit
from pathlib import Path
from typing import List, Optional
from datetime import datetime
from models.job import Job
from core.paths import get_jobs_file
from core.error_recovery import retry_with_backoff, GracefulDegradation


class JobStorage:
    """Manages persistent storage of jobs in YAML format"""

    # Class-level write queue and worker thread (singleton)
    _write_queue = None
    _writer_thread = None
    _shutdown = False

    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize JobStorage

        Args:
            storage_path: Path to YAML file (defaults to configured data directory)
        """
        if storage_path:
            self.storage_path = Path(storage_path)
        else:
            self.storage_path = get_jobs_file()

        # Ensure directory exists
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        # Create empty file if it doesn't exist
        if not self.storage_path.exists():
            self._write_jobs_immediate([])

        # Initialize write queue and worker thread (singleton)
        if JobStorage._write_queue is None:
            JobStorage._write_queue = queue.Queue()
            JobStorage._writer_thread = threading.Thread(
                target=JobStorage._write_worker,
                daemon=True,
                name="JobStorageWriter"
            )
            JobStorage._writer_thread.start()
            # Register cleanup on exit
            atexit.register(JobStorage._shutdown_writer)

    def save_job(self, job: Job) -> bool:
        """
        Save a job to storage (create or update)

        Args:
            job: Job instance to save

        Returns:
            True if successful, False otherwise
        """
        try:
            jobs = self.load_jobs()

            # Check if job already exists
            existing_index = None
            for i, existing_job in enumerate(jobs):
                if existing_job.id == job.id:
                    existing_index = i
                    break

            # Update or append
            if existing_index is not None:
                jobs[existing_index] = job
            else:
                jobs.append(job)

            # Write back to file
            self._write_jobs(jobs)
            return True

        except Exception as e:
            import logging
            logging.error(f"Error saving job: {e}")
            return False

    def load_jobs(self) -> List[Job]:
        """
        Load all jobs from storage with corruption detection and recovery

        Returns:
            List of Job instances
        """
        import logging

        try:
            data = self._load_and_validate_yaml(self.storage_path)

            # Handle empty file
            if not data or 'jobs' not in data:
                return []

            jobs = []
            for job_dict in data['jobs']:
                try:
                    job = Job.from_dict(job_dict)
                    jobs.append(job)
                except Exception as e:
                    logging.error(f"Error loading job {job_dict.get('id', 'unknown')}: {e}")
                    continue

            return jobs

        except FileNotFoundError:
            return []
        except Exception as e:
            logging.error(f"Error loading jobs: {e}")
            return []

    def _load_and_validate_yaml(self, file_path: Path) -> dict:
        """
        Load and validate YAML file with corruption detection and recovery

        Args:
            file_path: Path to YAML file

        Returns:
            Parsed YAML data

        Raises:
            Exception: If file cannot be loaded or recovered
        """
        import logging

        try:
            # Try to load the main file
            with open(file_path, 'r') as f:
                data = yaml.safe_load(f)

            # Validate structure
            if data is not None and not isinstance(data, dict):
                raise ValueError(f"Invalid YAML structure: expected dict, got {type(data)}")

            # If data has 'jobs' key, validate it's a list
            if data and 'jobs' in data:
                if not isinstance(data['jobs'], list):
                    raise ValueError(f"Invalid jobs structure: expected list, got {type(data['jobs'])}")

            return data

        except yaml.YAMLError as e:
            # YAML syntax error - attempt recovery from backup
            logging.error(f"YAML corruption detected in {file_path}: {e}")
            return self._recover_from_backup(file_path)

        except ValueError as e:
            # Structure validation error - attempt recovery from backup
            logging.error(f"Invalid YAML structure in {file_path}: {e}")
            return self._recover_from_backup(file_path)

        except Exception as e:
            # Other errors - attempt recovery from backup
            logging.error(f"Error reading {file_path}: {e}")
            return self._recover_from_backup(file_path)

    def _recover_from_backup(self, file_path: Path) -> dict:
        """
        Attempt to recover data from backup file

        Args:
            file_path: Path to corrupted file

        Returns:
            Recovered YAML data

        Raises:
            Exception: If backup doesn't exist or is also corrupted
        """
        import logging

        backup_path = file_path.with_suffix('.bak')

        if not backup_path.exists():
            logging.error(f"No backup file found at {backup_path}, cannot recover")
            raise FileNotFoundError(f"Backup file not found: {backup_path}")

        try:
            logging.warning(f"Attempting to recover from backup: {backup_path}")

            # Load backup file
            with open(backup_path, 'r') as f:
                data = yaml.safe_load(f)

            # Validate backup structure
            if data is not None and not isinstance(data, dict):
                raise ValueError(f"Backup has invalid structure: expected dict, got {type(data)}")

            if data and 'jobs' in data:
                if not isinstance(data['jobs'], list):
                    raise ValueError(f"Backup has invalid jobs structure: expected list, got {type(data['jobs'])}")

            # Recovery successful - restore from backup
            logging.info(f"Successfully recovered from backup, restoring {file_path}")
            shutil.copy2(backup_path, file_path)

            return data

        except Exception as e:
            logging.error(f"Backup file is also corrupted: {e}")
            # Last resort: return empty structure
            logging.warning("Creating new empty jobs file")
            return {'jobs': []}

    def get_job(self, job_id: str) -> Optional[Job]:
        """
        Get a specific job by ID

        Args:
            job_id: Job ID to retrieve

        Returns:
            Job instance or None if not found
        """
        jobs = self.load_jobs()
        for job in jobs:
            if job.id == job_id:
                return job
        return None

    def delete_job(self, job_id: str) -> bool:
        """
        Delete a job from storage

        Args:
            job_id: ID of job to delete

        Returns:
            True if deleted, False if not found or error
        """
        try:
            jobs = self.load_jobs()
            original_count = len(jobs)

            # Filter out the job to delete
            jobs = [job for job in jobs if job.id != job_id]

            # Check if anything was deleted
            if len(jobs) == original_count:
                return False  # Job not found

            # Write back to file
            self._write_jobs(jobs)
            return True

        except Exception as e:
            import logging
            logging.error(f"Error deleting job: {e}")
            return False

    def update_job(self, job: Job) -> bool:
        """
        Update an existing job

        Args:
            job: Job instance with updated data

        Returns:
            True if successful, False if job not found or error
        """
        try:
            jobs = self.load_jobs()

            # Find and update the job
            found = False
            for i, existing_job in enumerate(jobs):
                if existing_job.id == job.id:
                    jobs[i] = job
                    found = True
                    break

            if not found:
                return False

            # Write back to file
            self._write_jobs(jobs)
            return True

        except Exception as e:
            import logging
            logging.error(f"Error updating job: {e}")
            return False

    def _write_jobs(self, jobs: List[Job]):
        """
        Queue a write operation (non-blocking)

        Args:
            jobs: List of Job instances to write
        """
        if JobStorage._shutdown:
            # If shutting down, write immediately
            self._write_jobs_immediate(jobs)
            return

        # Queue the write operation
        JobStorage._write_queue.put(('write', jobs, self.storage_path))

    def _write_jobs_immediate(self, jobs: List[Job]):
        """
        Write jobs to file immediately with file locking, backup, and atomic write

        Args:
            jobs: List of Job instances to write
        """
        JobStorage._perform_write(jobs, self.storage_path)

    @staticmethod
    @retry_with_backoff(max_retries=3, initial_delay=0.5, component="storage", log_errors=True)
    def _perform_write(jobs: List[Job], storage_path: Path):
        """
        Perform the actual file write with locking and backup
        Uses automatic retry with exponential backoff for transient failures (Task 6.3)

        Args:
            jobs: List of Job instances to write
            storage_path: Path to write to
        """
        import logging

        # Create backup before writing (keep last successful write)
        if storage_path.exists():
            backup_path = storage_path.with_suffix('.bak')
            try:
                shutil.copy2(storage_path, backup_path)
            except Exception as e:
                logging.warning(f"Failed to create backup: {e}")

        # Convert jobs to dict format
        jobs_data = {
            'jobs': [job.to_dict() for job in jobs]
        }

        # Write to temporary file first (atomic write)
        temp_path = storage_path.with_suffix('.tmp')
        lock_path = storage_path.with_suffix('.lock')

        lock_file = None
        try:
            # Create/open lock file and acquire exclusive lock
            lock_file = open(lock_path, 'w')
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)

            # Write to temp file while holding lock
            with open(temp_path, 'w') as f:
                yaml.safe_dump(jobs_data, f, default_flow_style=False, sort_keys=False)

            # Atomic rename
            temp_path.replace(storage_path)

        except Exception as e:
            logging.error(f"Error writing jobs file: {e}")
            # Clean up temp file if it exists
            if temp_path.exists():
                temp_path.unlink()
            raise e
        finally:
            # Release lock and close lock file
            if lock_file:
                try:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
                    lock_file.close()
                except Exception as e:
                    logging.warning(f"Error releasing file lock: {e}")

    @staticmethod
    def _write_worker():
        """
        Background thread that processes write operations from the queue
        """
        import logging
        logging.info("JobStorage write worker started")

        while not JobStorage._shutdown:
            try:
                # Get write operation from queue (with timeout for clean shutdown)
                try:
                    operation = JobStorage._write_queue.get(timeout=1.0)
                except queue.Empty:
                    continue

                if operation is None:  # Shutdown signal
                    break

                op_type, jobs, storage_path = operation

                if op_type == 'write':
                    # Perform the actual write
                    try:
                        JobStorage._perform_write(jobs, storage_path)
                    except Exception as e:
                        logging.error(f"Write worker error: {e}")

                # Mark task as done
                JobStorage._write_queue.task_done()

            except Exception as e:
                import logging
                logging.error(f"Write worker exception: {e}")

        logging.info("JobStorage write worker stopped")

    @classmethod
    def _shutdown_writer(cls):
        """
        Shutdown the write worker thread cleanly
        """
        import logging
        if cls._writer_thread and cls._writer_thread.is_alive():
            logging.info("Shutting down JobStorage write worker...")
            cls._shutdown = True

            # Wait for queue to empty
            if cls._write_queue:
                cls._write_queue.join()

            # Send shutdown signal
            if cls._write_queue:
                cls._write_queue.put(None)

            # Wait for thread to finish
            cls._writer_thread.join(timeout=5.0)
            logging.info("JobStorage write worker shut down")

    def clear_all(self) -> bool:
        """
        Clear all jobs from storage

        Returns:
            True if successful
        """
        try:
            self._write_jobs([])
            return True
        except Exception as e:
            import logging
            logging.error(f"Error clearing jobs: {e}")
            return False

    def count_jobs(self) -> int:
        """
        Get count of stored jobs

        Returns:
            Number of jobs in storage
        """
        return len(self.load_jobs())
