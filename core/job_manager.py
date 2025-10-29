"""
Job Manager - Central controller for all backup jobs
"""
import time
import threading
from typing import Dict, List, Optional, Tuple
from models.job import Job
from storage.job_storage import JobStorage
from engines.rsync_engine import RsyncEngine
from utils.validation import validate_job_before_start
from utils.safety_checks import validate_deletion_safety
from utils.deletion_logger import DeletionLogger
from core.error_recovery import GracefulDegradation, get_circuit_breaker
from core.error_repository import get_error_repository
from models.error_event import ErrorEvent
from utils.rwlock import ReadWriteLock


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
            self.last_progress_save: Dict[str, Tuple[float, int]] = {}  # job_id -> (timestamp, percent)
            self.engine_stop_times: Dict[str, float] = {}  # job_id -> timestamp when engine stopped
            
            # TASK 7.4: Use read-write lock for better concurrency
            # Replace single RLock with ReadWriteLock for improved read performance
            self._rwlock = ReadWriteLock("JobManager")
            # Keep legacy lock names for compatibility
            self._lock = self._rwlock  # For backward compatibility
            self._engines_lock = threading.Lock()  # Protect engines dict access

            # Job list cache (Task 7.1)
            self._job_list_cache: Optional[List[Dict]] = None
            self._job_list_cache_time: float = 0.0
            self._job_list_dirty: bool = True

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
        # TASK 7.4: Use write lock for job creation (exclusive access)
        with self._rwlock.write_lock():
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
                    self._mark_job_list_dirty()  # Invalidate cache
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
        # TASK 7.4: Use write lock for starting jobs (modifies state)
        with self._rwlock.write_lock():
            try:
                # Check if already running
                with self._engines_lock:
                    if job_id in self.engines and self.engines[job_id].is_running():
                        return False, "Job is already running"

                # Load job from storage
                job = self.storage.get_job(job_id)
                if not job:
                    return False, f"Job {job_id} not found"

                # Enforce valid status transitions
                valid_start_statuses = [Job.STATUS_PENDING, Job.STATUS_PAUSED, Job.STATUS_FAILED]
                if job.status not in valid_start_statuses:
                    if job.status == Job.STATUS_RUNNING:
                        return False, "Job is already running"
                    elif job.status == Job.STATUS_COMPLETED:
                        return False, "Cannot start completed job. Create a new job or delete this one."
                    else:
                        return False, f"Cannot start job with status '{job.status}'"

                # Validate paths before starting
                valid, error_msg = job.validate_paths()
                if not valid:
                    return False, f"Path validation failed: {error_msg}"

                # Comprehensive validation (disk space, permissions, etc.)
                valid, error_msg = validate_job_before_start(job.source, job.dest, job.type)
                if not valid:
                    return False, f"Pre-start validation failed: {error_msg}"

                # Safety checks for deletion (if enabled)
                deletion_logger = None
                if job.should_delete_source():
                    # Run safety checks before starting job with deletion
                    safe, safety_msg = validate_deletion_safety(
                        job.source,
                        job.dest,
                        require_space_check=True
                    )
                    if not safe:
                        return False, f"Deletion safety check failed: {safety_msg}"

                    # Create deletion logger for this job
                    deletion_logger = DeletionLogger(job.id)
                    deletion_logger.log_deletion_start(
                        mode=job.deletion_mode,
                        total_files=0  # Will be updated during backup
                    )

                # Create appropriate engine
                # Get settings including verification mode
                from core.settings import get_settings
                settings = get_settings()
                max_retries = settings.get('max_retry_attempts', 10)
                verification_mode = settings.get('verification_mode', 'fast')

                engine = None
                if job.type == Job.TYPE_RSYNC:
                    engine = RsyncEngine(
                        source=job.source,
                        dest=job.dest,
                        job_id=job.id,
                        bandwidth_limit=job.settings.get('bandwidth_limit'),
                        max_retries=max_retries,
                        verification_mode=verification_mode,
                        delete_source_after=job.should_delete_source(),
                        deletion_mode=job.deletion_mode,
                        deletion_logger=deletion_logger
                    )
                elif job.type == Job.TYPE_RCLONE:
                    # Preflight check: verify rclone is installed
                    from utils.rclone_helper import is_rclone_installed
                    is_installed, _ = is_rclone_installed()
                    if not is_installed:
                        raise ValueError("rclone not found. Install from https://rclone.org")

                    # Import here to avoid circular dependency if rclone engine imports Job
                    try:
                        from engines.rclone_engine import RcloneEngine
                        engine = RcloneEngine(
                            source=job.source,
                            dest=job.dest,
                            job_id=job.id,
                            bandwidth_limit=job.settings.get('bandwidth_limit'),
                            max_retries=max_retries,
                            verification_mode=verification_mode,
                            delete_source_after=job.should_delete_source(),
                            deletion_mode=job.deletion_mode,
                            deletion_logger=deletion_logger
                        )
                    except ImportError:
                        return False, "Rclone engine not yet implemented"
                else:
                    return False, f"Unknown job type: {job.type}"

                # Start engine
                if engine.start():
                    engine_started = True
                    try:
                        with self._engines_lock:
                            self.engines[job_id] = engine
                            # Initialize progress tracking for periodic persistence
                            self.last_progress_save[job_id] = (time.time(), 0)

                        job.update_status(Job.STATUS_RUNNING)
                        self.storage.update_job(job)
                        self._mark_job_list_dirty()  # Invalidate cache when status changes

                        return True, f"Job '{job.name}' started successfully"
                    except Exception as e:
                        # Clean up engine if post-start operations failed
                        import logging
                        logging.error(f"Post-start failure for job {job_id}, cleaning up engine: {e}")
                        with self._engines_lock:
                            if job_id in self.engines:
                                try:
                                    self.engines[job_id].stop()
                                except Exception:
                                    pass  # Best effort cleanup
                                del self.engines[job_id]
                            if job_id in self.last_progress_save:
                                del self.last_progress_save[job_id]
                        raise  # Re-raise to be caught by outer handler
                else:
                    return False, "Failed to start backup engine"

            except Exception as e:
                return False, f"Error starting job: {str(e)}"

    def stop_job(self, job_id: str) -> Tuple[bool, str]:
        """
        Stop a backup job (pause)

        Args:
            job_id: ID of job to stop

        Returns:
            Tuple of (success, message)
        """
        # TASK 7.4: Use write lock for stopping jobs (modifies state)
        with self._rwlock.write_lock():
            try:
                # Check if job is running and get engine
                with self._engines_lock:
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
                        self._mark_job_list_dirty()  # Invalidate cache when status changes

                    # Clean up engine from memory
                    with self._engines_lock:
                        del self.engines[job_id]
                        # Clean up progress tracking
                        if job_id in self.last_progress_save:
                            del self.last_progress_save[job_id]

                    return True, f"Job stopped successfully"
                else:
                    return False, "Failed to stop backup engine"

            except Exception as e:
                return False, f"Error stopping job: {str(e)}"

    def get_job_status(self, job_id: str) -> Optional[Dict]:
        """
        Get current status and progress of a job (READ-ONLY)

        This method is now read-only and does not modify job state.
        Use update_job_from_engine() to update job state from engine progress.

        Args:
            job_id: ID of job to query

        Returns:
            Dict with job info and current progress, or None if not found
        """
        # TASK 7.4: Use read lock for status queries (allows concurrent reads)
        with self._rwlock.read_lock():
            try:
                job = self.storage.get_job(job_id)
                if not job:
                    return None

                # If job is running, get live progress from engine (read-only)
                live_progress = None
                with self._engines_lock:
                    if job_id in self.engines:
                        engine = self.engines[job_id]
                        if engine.is_running():
                            live_progress = engine.get_progress()

                # Return job data with live progress if available
                result = {
                    'id': job.id,
                    'name': job.name,
                    'source': job.source,
                    'dest': job.dest,
                    'type': job.type,
                    'status': job.status,
                    'progress': live_progress if live_progress else job.progress,
                    'settings': job.settings,
                    'created_at': job.created_at,
                    'updated_at': job.updated_at
                }

                return result

            except Exception as e:
                import logging
                logging.error(f"Error getting job status: {e}")
                return None

    def update_job_from_engine(self, job_id: str) -> Tuple[bool, str]:
        """
        Update job state from engine progress (WRITE operation)

        This method handles all job state modifications based on engine status.
        Should be called periodically by background monitor.

        Args:
            job_id: ID of job to update

        Returns:
            Tuple of (updated, message) - updated is True if job was modified
        """
        # TASK 7.4: Use write lock for updating job state
        with self._rwlock.write_lock():
            try:
                job = self.storage.get_job(job_id)
                if not job:
                    return False, f"Job {job_id} not found"

                # Capture current version for optimistic locking
                original_version = job.version

                # Get engine
                with self._engines_lock:
                    if job_id not in self.engines:
                        return False, "No engine found for job"
                    engine = self.engines[job_id]

                # Update based on engine state
                if engine.is_running():
                    # Get live progress and update job
                    live_progress = engine.get_progress()
                    job.update_progress(live_progress)

                    # Persist progress periodically (throttled)
                    if self._should_persist_progress(job_id, live_progress):
                        # Check for concurrent modifications before saving
                        storage_job = self.storage.get_job(job_id)
                        if storage_job and storage_job.version != original_version:
                            import logging
                            logging.warning(
                                f"Concurrent modification detected for job {job_id}: "
                                f"original_version={original_version}, storage_version={storage_job.version}. "
                                f"Proceeding with update (last write wins)."
                            )

                        self.storage.update_job(job)
                        current_percent = live_progress.get('percent', 0)
                        with self._engines_lock:
                            self.last_progress_save[job_id] = (time.time(), current_percent)

                    return True, "Progress updated"
                else:
                    # Engine stopped - save final state and clean up
                    final_progress = engine.get_progress()
                    job.update_progress(final_progress)

                    # CRITICAL: Save final progress BEFORE updating status
                    # This ensures we don't lose progress data if app crashes during status update
                    import logging
                    storage_job = self.storage.get_job(job_id)
                    if storage_job and storage_job.version != original_version:
                        logging.warning(
                            f"Concurrent modification detected for job {job_id} during final progress save: "
                            f"original_version={original_version}, storage_version={storage_job.version}. "
                            f"Proceeding with update (last write wins)."
                        )

                    logging.info(f"Saving final progress for job {job_id} before status change")
                    self.storage.update_job(job)

                    # Update version after first save
                    original_version = job.version

                    # Update status based on engine result
                    if final_progress.get('status') == 'completed':
                        job.update_status(Job.STATUS_COMPLETED)
                    elif final_progress.get('status') == 'failed':
                        job.update_status(Job.STATUS_FAILED)

                    # Check for concurrent modifications before final status save
                    storage_job = self.storage.get_job(job_id)
                    if storage_job and storage_job.version != original_version:
                        logging.warning(
                            f"Concurrent modification detected for job {job_id} during final status save: "
                            f"original_version={original_version}, storage_version={storage_job.version}. "
                            f"Proceeding with final update (last write wins)."
                        )

                    # Save final status
                    logging.info(f"Saving final status {job.status} for job {job_id}")
                    self.storage.update_job(job)
                    self._mark_job_list_dirty()  # Invalidate cache when status changes

                    # Clean up engine and tracking data
                    with self._engines_lock:
                        del self.engines[job_id]
                        if job_id in self.last_progress_save:
                            del self.last_progress_save[job_id]
                        # No need to track stop time since we're cleaning up immediately
                        if job_id in self.engine_stop_times:
                            del self.engine_stop_times[job_id]

                    import logging
                    logging.info(f"Engine cleanup: job {job_id} finished with status {job.status}")
                    return True, f"Job completed with status: {job.status}"

            except Exception as e:
                import logging
                logging.error(f"Error updating job from engine {job_id}: {e}")

                # Try to clean up engine if it's stopped (best effort)
                try:
                    with self._engines_lock:
                        if job_id in self.engines:
                            engine = self.engines[job_id]
                            if not engine.is_running():
                                logging.info(f"Cleaning up stopped engine for job {job_id} after exception")
                                del self.engines[job_id]
                                if job_id in self.last_progress_save:
                                    del self.last_progress_save[job_id]
                except Exception as cleanup_error:
                    logging.error(f"Failed to cleanup engine after exception: {cleanup_error}")

                return False, str(e)

    def cleanup_stopped_engines(self) -> int:
        """
        Clean up stopped engines from memory (Task 2.1-2.5)

        Removes engines that have been stopped for more than 5 minutes.
        Should be called periodically by background monitor.

        Returns:
            Number of engines cleaned up
        """
        # TASK 7.4: Use write lock for engine cleanup (modifies engines dict)
        with self._rwlock.write_lock():
            current_time = time.time()
            max_retention_time = 300  # 5 minutes
            cleaned_count = 0

            with self._engines_lock:
                # Find engines to clean up
                job_ids_to_cleanup = []
                
                for job_id in list(self.engines.keys()):
                    engine = self.engines[job_id]
                    
                    # Check if engine is stopped
                    if not engine.is_running():
                        # Check stop time
                        if job_id in self.engine_stop_times:
                            stop_time = self.engine_stop_times[job_id]
                            time_since_stop = current_time - stop_time
                            
                            if time_since_stop > max_retention_time:
                                job_ids_to_cleanup.append(job_id)
                                logging.info(f"Cleaning up stopped engine for job {job_id} (stopped {time_since_stop:.0f}s ago)")
                        else:
                            # No stop time recorded, mark it now
                            self.engine_stop_times[job_id] = current_time
                
                # Clean up identified engines
                for job_id in job_ids_to_cleanup:
                    del self.engines[job_id]
                    if job_id in self.engine_stop_times:
                        del self.engine_stop_times[job_id]
                    if job_id in self.last_progress_save:
                        del self.last_progress_save[job_id]
                    cleaned_count += 1
            
            if cleaned_count > 0:
                logging.info(f"Cleaned up {cleaned_count} stopped engine(s)")
            
            return cleaned_count

    def _should_persist_progress(self, job_id: str, progress: Dict) -> bool:
        """
        Check if progress should be persisted to disk.
        Throttles saves to prevent excessive I/O.

        Args:
            job_id: ID of the job
            progress: Current progress dict

        Returns:
            True if progress should be saved now
        """
        current_time = time.time()
        current_percent = progress.get('percent', 0)

        with self._engines_lock:
            # First save for this job
            if job_id not in self.last_progress_save:
                return True

            last_time, last_percent = self.last_progress_save[job_id]

        # Save if 2+ seconds elapsed OR 1%+ progress change
        time_elapsed = (current_time - last_time) >= 2.0
        significant_change = abs(current_percent - last_percent) >= 1

        return time_elapsed or significant_change
    
    def list_jobs(self) -> List[Dict]:
        """
        List all jobs with current status
        Uses 1-second cache with dirty checking (Task 7.1)

        Returns:
            List of job info dictionaries
        """
        # TASK 7.4: Use read lock for listing jobs (allows concurrent reads)
        with self._rwlock.read_lock():
            current_time = time.time()

            # Check if cache is valid (less than 1 second old and not dirty)
            if (not self._job_list_dirty and
                self._job_list_cache is not None and
                (current_time - self._job_list_cache_time) < 1.0):
                return self._job_list_cache

            # Cache miss or expired - rebuild cache
            jobs = self.storage.load_jobs()
            result = []

            for job in jobs:
                job_info = self.get_job_status(job.id)
                if job_info:
                    result.append(job_info)

            # Update cache
            self._job_list_cache = result
            self._job_list_cache_time = current_time
            self._job_list_dirty = False

            return result

    def _mark_job_list_dirty(self):
        """Mark job list cache as dirty (needs refresh)"""
        self._job_list_dirty = True
    
    def delete_job(self, job_id: str) -> Tuple[bool, str]:
        """
        Delete a job

        Args:
            job_id: ID of job to delete

        Returns:
            Tuple of (success, message)
        """
        # TASK 7.4: Use write lock for job deletion
        with self._rwlock.write_lock():
            try:
                # Check if job is running
                with self._engines_lock:
                    if job_id in self.engines and self.engines[job_id].is_running():
                        return False, "Cannot delete a running job"

                # Delete from storage
                if self.storage.delete_job(job_id):
                    # Clean up from engines dict if present
                    with self._engines_lock:
                        if job_id in self.engines:
                            del self.engines[job_id]
                    
                    self._mark_job_list_dirty()
                    return True, "Job deleted successfully"
                else:
                    return False, "Job not found"

            except Exception as e:
                return False, f"Error deleting job: {str(e)}"

