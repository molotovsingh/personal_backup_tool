"""
Test Phase 8.1: Concurrent Job Operations
Tests for concurrent job start/stop/status operations to verify thread safety.
"""
import pytest
import tempfile
import shutil
from pathlib import Path
import threading
import time
from core.job_manager import JobManager
from models.job import Job


@pytest.fixture
def test_dirs():
    """Create temporary test directories."""
    temp_dir = tempfile.mkdtemp()
    source_dir = Path(temp_dir) / "source"
    dest_dir = Path(temp_dir) / "dest"
    source_dir.mkdir()
    dest_dir.mkdir()

    # Create test files
    for i in range(10):
        (source_dir / f"file_{i}.txt").write_text(f"Content {i}")

    yield {"source": str(source_dir), "dest": str(dest_dir)}

    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def job_manager():
    """Get JobManager singleton and reset state."""
    manager = JobManager()
    # Clear any existing jobs for clean test
    return manager


def test_concurrent_job_creation(test_dirs, job_manager):
    """Test creating multiple jobs concurrently."""
    job_ids = []
    errors = []

    def create_job(index):
        try:
            success, msg, job = job_manager.create_job(
                name=f"Concurrent Test Job {index}",
                source=test_dirs['source'],
                dest=test_dirs['dest'],
                job_type=Job.TYPE_RSYNC
            )
            if success:
                job_ids.append(job.id)
            else:
                errors.append(msg)
        except Exception as e:
            errors.append(str(e))

    # Create 10 jobs concurrently
    threads = []
    for i in range(10):
        t = threading.Thread(target=create_job, args=(i,))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    # Verify all jobs were created successfully
    assert len(job_ids) == 10, f"Expected 10 jobs, got {len(job_ids)}. Errors: {errors}"
    assert len(errors) == 0, f"Unexpected errors: {errors}"

    # Verify jobs can be retrieved
    jobs = job_manager.list_jobs()
    assert len(jobs) >= 10, f"Expected at least 10 jobs in list, got {len(jobs)}"


def test_concurrent_job_status_reads(test_dirs, job_manager):
    """Test reading job status concurrently from multiple threads."""
    # Create a job first
    success, msg, job = job_manager.create_job(
        name="Status Read Test",
        source=test_dirs['source'],
        dest=test_dirs['dest'],
        job_type=Job.TYPE_RSYNC
    )
    assert success, f"Failed to create job: {msg}"
    job_id = job.id

    results = []
    errors = []

    def read_status():
        try:
            for _ in range(100):
                status = job_manager.get_job_status(job_id)
                results.append(status)
                time.sleep(0.001)  # Small delay
        except Exception as e:
            errors.append(str(e))

    # Read status from 10 threads concurrently
    threads = []
    for i in range(10):
        t = threading.Thread(target=read_status)
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    # Verify no errors occurred
    assert len(errors) == 0, f"Errors during concurrent reads: {errors}"
    # Verify we got 1000 results (10 threads * 100 reads)
    assert len(results) == 1000, f"Expected 1000 results, got {len(results)}"
    # Verify all results are valid
    assert all(r is not None for r in results), "Some status reads returned None"


def test_concurrent_start_stop_operations(test_dirs, job_manager):
    """Test starting and stopping the same job from multiple threads."""
    # Create a job
    success, msg, job = job_manager.create_job(
        name="Start/Stop Test",
        source=test_dirs['source'],
        dest=test_dirs['dest'],
        job_type=Job.TYPE_RSYNC
    )
    assert success, f"Failed to create job: {msg}"
    job_id = job.id

    start_successes = []
    stop_successes = []
    errors = []

    def try_start():
        try:
            success, msg = job_manager.start_job(job_id)
            start_successes.append(success)
        except Exception as e:
            errors.append(f"Start error: {str(e)}")

    def try_stop():
        try:
            time.sleep(0.1)  # Wait a bit before trying to stop
            success, msg = job_manager.stop_job(job_id)
            stop_successes.append(success)
        except Exception as e:
            errors.append(f"Stop error: {str(e)}")

    # Try to start the job from 3 threads concurrently
    threads = []
    for i in range(3):
        t = threading.Thread(target=try_start)
        threads.append(t)
        t.start()

    # Try to stop from 2 threads
    for i in range(2):
        t = threading.Thread(target=try_stop)
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    # Should have no exceptions
    assert len(errors) == 0, f"Errors during concurrent start/stop: {errors}"

    # At least one start should succeed
    assert any(start_successes), "No start operation succeeded"

    # Only one start should actually succeed (job can only start once)
    # The others should fail with "already running" or similar
    successful_starts = sum(1 for s in start_successes if s)
    assert successful_starts == 1, f"Expected 1 successful start, got {successful_starts}"


def test_cache_invalidation_on_concurrent_modifications(test_dirs, job_manager):
    """Test that cache is properly invalidated during concurrent modifications."""
    # Create initial jobs
    job_ids = []
    for i in range(5):
        success, msg, job = job_manager.create_job(
            name=f"Cache Test Job {i}",
            source=test_dirs['source'],
            dest=test_dirs['dest'],
            job_type=Job.TYPE_RSYNC
        )
        assert success
        job_ids.append(job.id)

    # Get initial job list (should populate cache)
    initial_jobs = job_manager.list_jobs()
    initial_count = len(initial_jobs)

    results = []

    def modify_and_read():
        # Create a new job
        success, msg, job = job_manager.create_job(
            name=f"Modified Job {threading.current_thread().name}",
            source=test_dirs['source'],
            dest=test_dirs['dest'],
            job_type=Job.TYPE_RSYNC
        )
        # Immediately read job list (should reflect new job)
        jobs = job_manager.list_jobs()
        results.append(len(jobs))

    # Modify and read from multiple threads
    threads = []
    for i in range(3):
        t = threading.Thread(target=modify_and_read)
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    # Verify final count is correct
    final_jobs = job_manager.list_jobs()
    expected_count = initial_count + 3
    assert len(final_jobs) == expected_count, \
        f"Expected {expected_count} jobs, got {len(final_jobs)}. Cache may not have been invalidated properly."


def test_version_conflict_detection(test_dirs, job_manager):
    """Test that concurrent modifications are detected via version field."""
    # Create a job
    success, msg, job = job_manager.create_job(
        name="Version Test",
        source=test_dirs['source'],
        dest=test_dirs['dest'],
        job_type=Job.TYPE_RSYNC
    )
    assert success
    job_id = job.id

    # Start the job
    success, msg = job_manager.start_job(job_id)
    assert success

    # Give it time to start
    time.sleep(0.5)

    # Get job and check version
    status1 = job_manager.get_job_status(job_id)
    initial_version = status1.get('version', 0)

    # Update from engine (this increments version)
    if status1['status'] == 'running':
        job_manager.update_job_from_engine(job_id)

    # Get updated version
    status2 = job_manager.get_job_status(job_id)
    updated_version = status2.get('version', 0)

    # Version should have incremented
    assert updated_version > initial_version, \
        f"Version should increment on updates. Initial: {initial_version}, Updated: {updated_version}"

    # Stop the job
    job_manager.stop_job(job_id)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
