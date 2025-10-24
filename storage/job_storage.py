"""
Job storage manager - YAML-based persistence for backup jobs
"""
import yaml
from pathlib import Path
from typing import List, Optional
from models.job import Job


class JobStorage:
    """Manages persistent storage of jobs in YAML format"""

    def __init__(self, storage_path: Optional[str] = None):
        """
        Initialize JobStorage

        Args:
            storage_path: Path to YAML file (defaults to ~/backup-manager/jobs.yaml)
        """
        if storage_path:
            self.storage_path = Path(storage_path)
        else:
            self.storage_path = Path.home() / 'backup-manager' / 'jobs.yaml'

        # Ensure directory exists
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        # Create empty file if it doesn't exist
        if not self.storage_path.exists():
            self._write_jobs([])

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
            print(f"Error saving job: {e}")
            return False

    def load_jobs(self) -> List[Job]:
        """
        Load all jobs from storage

        Returns:
            List of Job instances
        """
        try:
            with open(self.storage_path, 'r') as f:
                data = yaml.safe_load(f)

            # Handle empty file
            if not data or 'jobs' not in data:
                return []

            jobs = []
            for job_dict in data['jobs']:
                try:
                    job = Job.from_dict(job_dict)
                    jobs.append(job)
                except Exception as e:
                    print(f"Error loading job {job_dict.get('id', 'unknown')}: {e}")
                    continue

            return jobs

        except FileNotFoundError:
            return []
        except Exception as e:
            print(f"Error loading jobs: {e}")
            return []

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
            print(f"Error deleting job: {e}")
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
            print(f"Error updating job: {e}")
            return False

    def _write_jobs(self, jobs: List[Job]):
        """
        Write jobs to file with atomic write (temp file + rename)

        Args:
            jobs: List of Job instances to write
        """
        # Convert jobs to dict format
        jobs_data = {
            'jobs': [job.to_dict() for job in jobs]
        }

        # Write to temporary file first (atomic write)
        temp_path = self.storage_path.with_suffix('.tmp')

        try:
            with open(temp_path, 'w') as f:
                yaml.safe_dump(jobs_data, f, default_flow_style=False, sort_keys=False)

            # Atomic rename
            temp_path.replace(self.storage_path)

        except Exception as e:
            # Clean up temp file if it exists
            if temp_path.exists():
                temp_path.unlink()
            raise e

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
            print(f"Error clearing jobs: {e}")
            return False

    def count_jobs(self) -> int:
        """
        Get count of stored jobs

        Returns:
            Number of jobs in storage
        """
        return len(self.load_jobs())
