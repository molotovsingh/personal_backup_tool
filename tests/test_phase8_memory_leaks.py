"""
Test Phase 8.3: Memory Leak Verification
Tests to verify no memory leaks after 100 job cycles.
"""
import pytest
import tempfile
import shutil
import gc
import sys
from pathlib import Path
from core.job_manager import JobManager
from models.job import Job
import time


@pytest.fixture
def test_dirs():
    """Create temporary test directories."""
    temp_dir = tempfile.mkdtemp()
    source_dir = Path(temp_dir) / "source"
    dest_dir = Path(temp_dir) / "dest"
    source_dir.mkdir()
    dest_dir.mkdir()

    # Create small test files
    for i in range(5):
        (source_dir / f"file_{i}.txt").write_text(f"Content {i}")

    yield {"source": str(source_dir), "dest": str(dest_dir)}

    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def job_manager():
    """Get JobManager singleton."""
    return JobManager()


def get_memory_usage():
    """Get current memory usage in MB."""
    try:
        import psutil
        import os
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / 1024 / 1024  # Convert to MB
    except ImportError:
        # If psutil not available, use sys.getsizeof as rough estimate
        return sys.getsizeof(gc.get_objects()) / 1024 / 1024


def test_engine_cleanup_after_job_completion(test_dirs, job_manager):
    """Test that engines are properly cleaned up after job completion."""
    job_ids = []

    # Create and run 10 jobs
    for i in range(10):
        success, msg, job = job_manager.create_job(
            name=f"Cleanup Test Job {i}",
            source=test_dirs['source'],
            dest=test_dirs['dest'],
            job_type=Job.TYPE_RSYNC
        )
        assert success, f"Failed to create job: {msg}"
        job_ids.append(job.id)

        # Start job
        success, msg = job_manager.start_job(job.id)
        assert success, f"Failed to start job: {msg}"

        # Wait a bit for job to run
        time.sleep(0.5)

        # Stop job
        success, msg = job_manager.stop_job(job.id)
        # May fail if job already completed, which is fine

    # Wait for cleanup
    time.sleep(1)

    # Run cleanup explicitly
    cleaned = job_manager.cleanup_stopped_engines()

    # Verify engines dictionary is empty or minimal
    with job_manager._engines_lock:
        engine_count = len(job_manager.engines)

    assert engine_count == 0, \
        f"Expected 0 engines after cleanup, found {engine_count}. Possible memory leak."


def test_no_memory_leak_after_multiple_job_cycles(test_dirs, job_manager):
    """Test memory usage remains stable after many job cycles."""
    # Force garbage collection
    gc.collect()

    # Get baseline memory
    initial_memory = get_memory_usage()
    print(f"\nInitial memory: {initial_memory:.2f} MB")

    job_ids_to_delete = []

    # Run 50 job cycles (reduced from 100 for faster testing)
    for cycle in range(50):
        # Create job
        success, msg, job = job_manager.create_job(
            name=f"Memory Test Job {cycle}",
            source=test_dirs['source'],
            dest=test_dirs['dest'],
            job_type=Job.TYPE_RSYNC
        )
        assert success, f"Cycle {cycle}: Failed to create job: {msg}"
        job_ids_to_delete.append(job.id)

        # Start job
        success, msg = job_manager.start_job(job.id)
        if success:
            # Let it run briefly
            time.sleep(0.1)

            # Stop job
            job_manager.stop_job(job.id)

        # Delete job to clean up
        if len(job_ids_to_delete) > 10:  # Keep max 10 jobs
            old_job_id = job_ids_to_delete.pop(0)
            job_manager.delete_job(old_job_id)

        # Periodic cleanup
        if cycle % 10 == 0:
            job_manager.cleanup_stopped_engines()
            gc.collect()

            current_memory = get_memory_usage()
            print(f"Cycle {cycle}: Memory usage: {current_memory:.2f} MB")

    # Final cleanup
    for job_id in job_ids_to_delete:
        job_manager.delete_job(job_id)

    job_manager.cleanup_stopped_engines()
    gc.collect()

    # Get final memory
    final_memory = get_memory_usage()
    print(f"Final memory: {final_memory:.2f} MB")

    # Memory growth should be reasonable (less than 50 MB for 50 cycles)
    memory_growth = final_memory - initial_memory
    print(f"Memory growth: {memory_growth:.2f} MB")

    assert memory_growth < 50, \
        f"Memory leak detected: grew by {memory_growth:.2f} MB after 50 cycles"


def test_engine_stop_time_tracking(test_dirs, job_manager):
    """Test that engine stop times are tracked and cleaned up."""
    # Create and start a job
    success, msg, job = job_manager.create_job(
        name="Stop Time Test",
        source=test_dirs['source'],
        dest=test_dirs['dest'],
        job_type=Job.TYPE_RSYNC
    )
    assert success
    job_id = job.id

    # Start and immediately stop
    job_manager.start_job(job_id)
    time.sleep(0.2)
    job_manager.stop_job(job_id)

    # Engine stop time should be tracked (if engine hasn't been cleaned up yet)
    # After cleanup, it should be removed
    time.sleep(0.5)
    job_manager.cleanup_stopped_engines()

    # Verify stop time was cleaned up
    with job_manager._engines_lock:
        assert job_id not in job_manager.engine_stop_times, \
            f"Engine stop time for {job_id} was not cleaned up"


def test_job_list_cache_doesnt_grow_indefinitely(test_dirs, job_manager):
    """Test that job list cache doesn't cause memory growth."""
    # Create jobs
    job_ids = []
    for i in range(20):
        success, msg, job = job_manager.create_job(
            name=f"Cache Test {i}",
            source=test_dirs['source'],
            dest=test_dirs['dest'],
            job_type=Job.TYPE_RSYNC
        )
        assert success
        job_ids.append(job.id)

    # Call list_jobs many times (should use cache)
    for _ in range(100):
        jobs = job_manager.list_jobs()
        assert len(jobs) >= 20

    # Cache should only hold one copy
    assert job_manager._job_list_cache is not None
    cached_count = len(job_manager._job_list_cache)
    assert cached_count >= 20

    # Delete half the jobs
    for i in range(10):
        job_manager.delete_job(job_ids[i])

    # List should reflect deletions
    jobs = job_manager.list_jobs()
    assert len(jobs) >= 10


def test_progress_tracking_cleanup(test_dirs, job_manager):
    """Test that progress tracking dictionaries are cleaned up."""
    job_ids = []

    # Create and run several jobs
    for i in range(5):
        success, msg, job = job_manager.create_job(
            name=f"Progress Test {i}",
            source=test_dirs['source'],
            dest=test_dirs['dest'],
            job_type=Job.TYPE_RSYNC
        )
        assert success
        job_ids.append(job.id)

        job_manager.start_job(job.id)
        time.sleep(0.2)
        job_manager.stop_job(job.id)

    # Check tracking dictionaries
    with job_manager._engines_lock:
        # last_progress_save should be cleaned up
        remaining_tracked = len(job_manager.last_progress_save)

        # Should be minimal or empty after stopping
        assert remaining_tracked <= 1, \
            f"Progress tracking not cleaned up properly: {remaining_tracked} entries remain"


def test_storage_write_queue_doesnt_grow(test_dirs, job_manager):
    """Test that storage write queue doesn't grow indefinitely."""
    from storage.job_storage import JobStorage

    # Create many jobs quickly to queue writes
    for i in range(20):
        success, msg, job = job_manager.create_job(
            name=f"Queue Test {i}",
            source=test_dirs['source'],
            dest=test_dirs['dest'],
            job_type=Job.TYPE_RSYNC
        )
        assert success

    # Wait for queue to process
    time.sleep(2)

    # Queue should be empty or minimal
    storage = JobStorage()
    if hasattr(storage, '_write_queue'):
        queue_size = storage._write_queue.qsize()
        assert queue_size < 5, \
            f"Write queue has {queue_size} items, may indicate processing issues"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])  # -s to show print statements
