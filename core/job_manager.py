"""
Job Manager - Central controller for all backup jobs
"""
from typing import Dict, List, Optional, Tuple
from models.job import Job
from storage.job_storage import JobStorage
from engines.rsync_engine import RsyncEngine
from utils.validation import validate_job_before_start


class JobManager:
    """Singleton manager for all backup jobs"""

    _instance = None
    _initialized = False

    def __new__(cls):
        """Enforce singleton pattern"""
        if cls._instance is None:
            cls._instance = super(JobManager, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize JobManager (only once due to singleton)"""
        if not JobManager._initialized:
            self.storage = JobStorage()
            self.engines: Dict[str, any] = {}  # job_id -> engine instance
            JobManager._initialized = True

    def create_job(
        self,
        name: str,
        source: str,
        dest: str,
        job_type: str,
        settings: Optional[Dict] = None
    ) -> Tuple[bool, str, Optional[Job]]:
        """
        Create a new backup job

        Args:
            name: Job name
            source: Source path
            dest: Destination path
            job_type: 'rsync' or 'rclone'
            settings: Optional settings dict (bandwidth_limit, etc.)

        Returns:
            Tuple of (success, message, job_instance)
        """
        try:
            # Create job instance
            job = Job(
                name=name,
                source=source,
                dest=dest,
                job_type=job_type,
                settings=settings or {}
            )

            # Validate paths
            valid, error_msg = job.validate_paths()
            if not valid:
                return False, error_msg, None

            # Save to storage
            if self.storage.save_job(job):
                return True, f"Job '{name}' created successfully", job
            else:
                return False, "Failed to save job to storage", None

        except Exception as e:
            return False, f"Error creating job: {str(e)}", None

    def start_job(self, job_id: str) -> Tuple[bool, str]:
        """
        Start a backup job

        Args:
            job_id: ID of job to start

        Returns:
            Tuple of (success, message)
        """
        try:
            # Check if already running
            if job_id in self.engines and self.engines[job_id].is_running():
                return False, "Job is already running"

            # Load job from storage
            job = self.storage.get_job(job_id)
            if not job:
                return False, f"Job {job_id} not found"

            # Validate paths before starting
            valid, error_msg = job.validate_paths()
            if not valid:
                return False, f"Path validation failed: {error_msg}"

            # Comprehensive validation (disk space, permissions, etc.)
            valid, error_msg = validate_job_before_start(job.source, job.dest, job.type)
            if not valid:
                return False, f"Pre-start validation failed: {error_msg}"

            # Create appropriate engine
            engine = None
            if job.type == Job.TYPE_RSYNC:
                engine = RsyncEngine(
                    source=job.source,
                    dest=job.dest,
                    job_id=job.id,
                    bandwidth_limit=job.settings.get('bandwidth_limit')
                )
            elif job.type == Job.TYPE_RCLONE:
                # Import here to avoid circular dependency if rclone engine imports Job
                try:
                    from engines.rclone_engine import RcloneEngine
                    engine = RcloneEngine(
                        source=job.source,
                        dest=job.dest,
                        job_id=job.id,
                        bandwidth_limit=job.settings.get('bandwidth_limit')
                    )
                except ImportError:
                    return False, "Rclone engine not yet implemented"
            else:
                return False, f"Unknown job type: {job.type}"

            # Start engine
            if engine.start():
                self.engines[job_id] = engine
                job.update_status(Job.STATUS_RUNNING)
                self.storage.update_job(job)
                return True, f"Job '{job.name}' started successfully"
            else:
                return False, "Failed to start backup engine"

        except Exception as e:
            return False, f"Error starting job: {str(e)}"

    def stop_job(self, job_id: str) -> Tuple[bool, str]:
        """
        Stop a running backup job

        Args:
            job_id: ID of job to stop

        Returns:
            Tuple of (success, message)
        """
        try:
            # Check if job is running
            if job_id not in self.engines:
                return False, "Job is not running"

            engine = self.engines[job_id]

            # Stop engine
            if engine.stop():
                # Update job status
                job = self.storage.get_job(job_id)
                if job:
                    # Get final progress from engine
                    final_progress = engine.get_progress()
                    job.update_progress(final_progress)
                    job.update_status(Job.STATUS_PAUSED)
                    self.storage.update_job(job)

                # Clean up engine from memory
                del self.engines[job_id]

                return True, f"Job stopped successfully"
            else:
                return False, "Failed to stop backup engine"

        except Exception as e:
            return False, f"Error stopping job: {str(e)}"

    def get_job_status(self, job_id: str) -> Optional[Dict]:
        """
        Get current status and progress of a job

        Args:
            job_id: ID of job to query

        Returns:
            Dict with job info and current progress, or None if not found
        """
        try:
            job = self.storage.get_job(job_id)
            if not job:
                return None

            # If job is running, get live progress from engine
            if job_id in self.engines:
                engine = self.engines[job_id]
                if engine.is_running():
                    live_progress = engine.get_progress()
                    job.update_progress(live_progress)
                    # Update storage periodically (but not on every call to avoid I/O)
                else:
                    # Engine stopped but still in memory, clean up
                    final_progress = engine.get_progress()
                    job.update_progress(final_progress)
                    if final_progress.get('status') == 'completed':
                        job.update_status(Job.STATUS_COMPLETED)
                    elif final_progress.get('status') == 'failed':
                        job.update_status(Job.STATUS_FAILED)
                    self.storage.update_job(job)
                    del self.engines[job_id]

            return {
                'id': job.id,
                'name': job.name,
                'source': job.source,
                'dest': job.dest,
                'type': job.type,
                'status': job.status,
                'progress': job.progress,
                'settings': job.settings,
                'created_at': job.created_at,
                'updated_at': job.updated_at
            }

        except Exception as e:
            print(f"Error getting job status: {e}")
            return None

    def list_jobs(self) -> List[Dict]:
        """
        List all jobs with current status

        Returns:
            List of job info dictionaries
        """
        jobs = self.storage.load_jobs()
        result = []

        for job in jobs:
            job_info = self.get_job_status(job.id)
            if job_info:
                result.append(job_info)

        return result

    def delete_job(self, job_id: str) -> Tuple[bool, str]:
        """
        Delete a job

        Args:
            job_id: ID of job to delete

        Returns:
            Tuple of (success, message)
        """
        try:
            # Stop job if running
            if job_id in self.engines:
                self.stop_job(job_id)

            # Delete from storage
            if self.storage.delete_job(job_id):
                return True, "Job deleted successfully"
            else:
                return False, "Job not found"

        except Exception as e:
            return False, f"Error deleting job: {str(e)}"

    def cleanup_stopped_engines(self):
        """Clean up engines that have finished running"""
        stopped_engines = []

        for job_id, engine in self.engines.items():
            if not engine.is_running():
                stopped_engines.append(job_id)

        for job_id in stopped_engines:
            engine = self.engines[job_id]
            final_progress = engine.get_progress()

            # Update job in storage
            job = self.storage.get_job(job_id)
            if job:
                job.update_progress(final_progress)
                if final_progress.get('status') == 'completed':
                    job.update_status(Job.STATUS_COMPLETED)
                elif final_progress.get('status') == 'failed':
                    job.update_status(Job.STATUS_FAILED)
                self.storage.update_job(job)

            del self.engines[job_id]
