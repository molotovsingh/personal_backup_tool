"""
Thread safety tests for JobManager

Tests concurrent access to JobManager methods to ensure thread safety.
"""
import pytest
import threading
import time
import tempfile
import os
from pathlib import Path
from core.job_manager import JobManager
from models.job import Job


class TestJobManagerThreadSafety:
    """Test thread safety of JobManager operations"""

    def setup_method(self):
        """Reset JobManager singleton before each test"""
        # Clear singleton instance for test isolation
        JobManager._instance = None
        JobManager._initialized = False
        self.manager = JobManager()

        # Create temp directory for test paths
        self.temp_dir = tempfile.mkdtemp()

        # Clean up any existing jobs from previous test runs
        # (important for test isolation when using persistent storage)
        jobs = self.manager.list_jobs()
        for job in jobs:
            self.manager.delete_job(job['id'])

    def teardown_method(self):
        """Clean up after each test"""
        # Delete all test jobs
        jobs = self.manager.list_jobs()
        for job in jobs:
            self.manager.delete_job(job['id'])

        # Clean up temp directory
        if hasattr(self, 'temp_dir') and os.path.exists(self.temp_dir):
            import shutil
            shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_concurrent_list_jobs(self):
        """
        Test concurrent list_jobs calls don't cause race conditions

        Creates 5 test jobs, then spawns 10 threads that each call list_jobs 100 times.
        Should complete without errors or data corruption.
        """
        # Create some test jobs with valid paths
        for i in range(5):
            src = Path(self.temp_dir) / f"test-src-{i}"
            dest = Path(self.temp_dir) / f"test-dest-{i}"
            src.mkdir(exist_ok=True)
            dest.mkdir(exist_ok=True)

            self.manager.create_job(
                name=f"test-job-{i}",
                source=str(src),
                dest=str(dest),
                job_type=Job.TYPE_RSYNC
            )

        errors = []
        thread_count = 10
        iterations = 100

        def list_jobs_worker():
            try:
                for _ in range(iterations):
                    jobs = self.manager.list_jobs()
                    assert len(jobs) == 5, f"Expected 5 jobs, got {len(jobs)}"
            except Exception as e:
                errors.append(str(e))

        # Spawn threads
        threads = []
        for _ in range(thread_count):
            thread = threading.Thread(target=list_jobs_worker)
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join(timeout=30)

        # Check for errors
        assert len(errors) == 0, f"Encountered errors: {errors}"

    def test_concurrent_creates(self):
        """
        Test concurrent create_job operations

        Spawns 10 threads that each create a unique job.
        Should result in exactly 10 jobs with no data corruption.
        """
        errors = []
        successful_creates = []
        thread_count = 10

        def create_job_worker(index):
            try:
                src = Path(self.temp_dir) / f"concurrent-src-{index}"
                dest = Path(self.temp_dir) / f"concurrent-dest-{index}"
                src.mkdir(exist_ok=True)
                dest.mkdir(exist_ok=True)

                success, msg, job = self.manager.create_job(
                    name=f"concurrent-job-{index}",
                    source=str(src),
                    dest=str(dest),
                    job_type=Job.TYPE_RSYNC
                )
                if success:
                    successful_creates.append(job.id)
                else:
                    errors.append(f"Create failed for job {index}: {msg}")
            except Exception as e:
                errors.append(f"Exception in thread {index}: {str(e)}")

        # Spawn threads
        threads = []
        for i in range(thread_count):
            thread = threading.Thread(target=create_job_worker, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join(timeout=30)

        # Verify results
        assert len(errors) == 0, f"Encountered errors: {errors}"
        assert len(successful_creates) == thread_count, \
            f"Expected {thread_count} successful creates, got {len(successful_creates)}"

        # Verify all jobs exist
        jobs = self.manager.list_jobs()
        assert len(jobs) == thread_count, f"Expected {thread_count} jobs, got {len(jobs)}"

    def test_concurrent_read_during_delete(self):
        """
        Test concurrent reads while deleting jobs

        Creates 10 jobs, then spawns reader threads that continuously list jobs
        while deleter threads delete jobs. Should not cause race conditions.
        """
        # Create test jobs
        job_ids = []
        for i in range(10):
            src = Path(self.temp_dir) / f"delete-src-{i}"
            dest = Path(self.temp_dir) / f"delete-dest-{i}"
            src.mkdir(exist_ok=True)
            dest.mkdir(exist_ok=True)

            success, msg, job = self.manager.create_job(
                name=f"delete-test-{i}",
                source=str(src),
                dest=str(dest),
                job_type=Job.TYPE_RSYNC
            )
            if success:
                job_ids.append(job.id)

        errors = []
        should_stop = threading.Event()

        def reader_worker():
            """Continuously read jobs"""
            try:
                while not should_stop.is_set():
                    jobs = self.manager.list_jobs()
                    # Just accessing the list, don't assert length
                    time.sleep(0.001)
            except Exception as e:
                errors.append(f"Reader error: {str(e)}")

        def deleter_worker(job_id):
            """Delete a specific job"""
            try:
                time.sleep(0.01)  # Small delay to let readers start
                success, msg = self.manager.delete_job(job_id)
                if not success and "not found" not in msg.lower():
                    errors.append(f"Delete failed for {job_id}: {msg}")
            except Exception as e:
                errors.append(f"Deleter error: {str(e)}")

        # Spawn reader threads
        reader_threads = []
        for _ in range(5):
            thread = threading.Thread(target=reader_worker)
            reader_threads.append(thread)
            thread.start()

        # Spawn deleter threads
        deleter_threads = []
        for job_id in job_ids:
            thread = threading.Thread(target=deleter_worker, args=(job_id,))
            deleter_threads.append(thread)
            thread.start()

        # Wait for deleters to finish
        for thread in deleter_threads:
            thread.join(timeout=30)

        # Stop readers
        should_stop.set()
        for thread in reader_threads:
            thread.join(timeout=5)

        # Check for errors
        assert len(errors) == 0, f"Encountered errors: {errors}"

        # Verify all jobs deleted
        remaining_jobs = self.manager.list_jobs()
        assert len(remaining_jobs) == 0, f"Expected 0 jobs, got {len(remaining_jobs)}"

    def test_concurrent_get_job_status(self):
        """
        Test concurrent get_job_status calls on the same job

        Creates 1 job, then spawns multiple threads that repeatedly call get_job_status.
        Should not cause race conditions or data corruption.
        """
        # Create a test job
        src = Path(self.temp_dir) / "status-src"
        dest = Path(self.temp_dir) / "status-dest"
        src.mkdir(exist_ok=True)
        dest.mkdir(exist_ok=True)

        success, msg, job = self.manager.create_job(
            name="status-test",
            source=str(src),
            dest=str(dest),
            job_type=Job.TYPE_RSYNC
        )
        assert success, f"Failed to create test job: {msg}"
        job_id = job.id

        errors = []
        thread_count = 10
        iterations = 50

        def status_worker():
            try:
                for _ in range(iterations):
                    status = self.manager.get_job_status(job_id)
                    assert status is not None, "get_job_status returned None"
                    assert status['id'] == job_id, "Job ID mismatch"
                    time.sleep(0.001)
            except Exception as e:
                errors.append(str(e))

        # Spawn threads
        threads = []
        for _ in range(thread_count):
            thread = threading.Thread(target=status_worker)
            threads.append(thread)
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join(timeout=30)

        # Check for errors
        assert len(errors) == 0, f"Encountered errors: {errors}"

    def test_no_dictionary_changed_size_errors(self):
        """
        Test that dictionary iteration doesn't cause 'dictionary changed size' errors

        This tests the specific Python threading issue where iterating over a dict
        while another thread modifies it causes RuntimeError.
        """
        errors = []
        should_stop = threading.Event()

        # Create initial jobs
        for i in range(5):
            src = Path(self.temp_dir) / f"dict-src-{i}"
            dest = Path(self.temp_dir) / f"dict-dest-{i}"
            src.mkdir(exist_ok=True)
            dest.mkdir(exist_ok=True)

            self.manager.create_job(
                name=f"dict-test-{i}",
                source=str(src),
                dest=str(dest),
                job_type=Job.TYPE_RSYNC
            )

        def list_worker():
            """Continuously list jobs (iterates over storage)"""
            try:
                while not should_stop.is_set():
                    self.manager.list_jobs()
                    time.sleep(0.001)
            except RuntimeError as e:
                if "dictionary changed size" in str(e):
                    errors.append(f"Dictionary iteration error: {str(e)}")
                else:
                    raise
            except Exception as e:
                errors.append(f"List worker error: {str(e)}")

        def create_delete_worker(index):
            """Create and delete jobs repeatedly"""
            try:
                for i in range(10):
                    # Create temporary directories
                    src = Path(self.temp_dir) / f"cd-src-{index}-{i}"
                    dest = Path(self.temp_dir) / f"cd-dest-{index}-{i}"
                    src.mkdir(exist_ok=True)
                    dest.mkdir(exist_ok=True)

                    # Create job
                    success, msg, job = self.manager.create_job(
                        name=f"cd-job-{index}-{i}",
                        source=str(src),
                        dest=str(dest),
                        job_type=Job.TYPE_RSYNC
                    )
                    if success:
                        time.sleep(0.002)
                        # Delete job
                        self.manager.delete_job(job.id)
                    time.sleep(0.001)
            except Exception as e:
                errors.append(f"Create/delete worker error: {str(e)}")

        # Spawn list workers
        list_threads = []
        for _ in range(3):
            thread = threading.Thread(target=list_worker)
            list_threads.append(thread)
            thread.start()

        # Spawn create/delete workers
        cd_threads = []
        for i in range(5):
            thread = threading.Thread(target=create_delete_worker, args=(i,))
            cd_threads.append(thread)
            thread.start()

        # Wait for create/delete workers
        for thread in cd_threads:
            thread.join(timeout=30)

        # Stop list workers
        should_stop.set()
        for thread in list_threads:
            thread.join(timeout=5)

        # Check for errors
        assert len(errors) == 0, f"Encountered errors: {errors}"
