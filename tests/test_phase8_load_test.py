"""
Test Phase 8.5: Load Test with 50+ Concurrent Jobs
Stress tests to verify system handles high load scenarios.
"""
import pytest
import tempfile
import shutil
from pathlib import Path
import threading
import time
from core.job_manager import JobManager
from models.job import Job
import concurrent.futures


@pytest.fixture
def test_dirs():
    """Create temporary test directories."""
    temp_dir = tempfile.mkdtemp()
    source_dir = Path(temp_dir) / "source"
    dest_dir = Path(temp_dir) / "dest"
    source_dir.mkdir()
    dest_dir.mkdir()

    # Create test files
    for i in range(3):
        (source_dir / f"file_{i}.txt").write_text(f"Content {i}")

    yield {"source": str(source_dir), "dest": str(dest_dir), "temp": temp_dir}

    # Cleanup
    shutil.rmtree(temp_dir)


@pytest.fixture
def job_manager():
    """Get JobManager singleton."""
    return JobManager()


def test_create_50_concurrent_jobs(test_dirs, job_manager):
    """Test creating 50 jobs concurrently."""
    job_ids = []
    errors = []
    lock = threading.Lock()

    def create_job(index):
        try:
            success, msg, job = job_manager.create_job(
                name=f"Load Test Job {index}",
                source=test_dirs['source'],
                dest=test_dirs['dest'],
                job_type=Job.TYPE_RSYNC
            )
            if success:
                with lock:
                    job_ids.append(job.id)
            else:
                with lock:
                    errors.append(f"Job {index}: {msg}")
        except Exception as e:
            with lock:
                errors.append(f"Job {index}: {str(e)}")

    # Use ThreadPoolExecutor for better control
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(create_job, i) for i in range(50)]
        concurrent.futures.wait(futures)

    # Verify results
    print(f"\nCreated {len(job_ids)} jobs")
    print(f"Errors: {len(errors)}")
    if errors:
        for error in errors[:5]:  # Print first 5 errors
            print(f"  {error}")

    assert len(job_ids) >= 45, \
        f"Expected at least 45 successful creations, got {len(job_ids)}. Errors: {errors[:3]}"


def test_start_multiple_jobs_concurrently(test_dirs, job_manager):
    """Test starting multiple jobs concurrently."""
    # Create 20 jobs first
    job_ids = []
    for i in range(20):
        success, msg, job = job_manager.create_job(
            name=f"Start Test Job {i}",
            source=test_dirs['source'],
            dest=test_dirs['dest'],
            job_type=Job.TYPE_RSYNC
        )
        if success:
            job_ids.append(job.id)

    assert len(job_ids) >= 15, "Need at least 15 jobs for start test"

    # Start them concurrently
    start_results = []
    errors = []
    lock = threading.Lock()

    def start_job(job_id):
        try:
            success, msg = job_manager.start_job(job_id)
            with lock:
                start_results.append((job_id, success, msg))
        except Exception as e:
            with lock:
                errors.append((job_id, str(e)))

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(start_job, job_id) for job_id in job_ids]
        concurrent.futures.wait(futures)

    # Verify at least some jobs started successfully
    successful_starts = sum(1 for _, success, _ in start_results if success)
    print(f"\nSuccessful starts: {successful_starts}/{len(job_ids)}")

    assert successful_starts >= 5, \
        f"Expected at least 5 successful starts, got {successful_starts}"


def test_list_jobs_performance_under_load(test_dirs, job_manager):
    """Test list_jobs performance with many jobs."""
    # Create 50 jobs
    for i in range(50):
        job_manager.create_job(
            name=f"Performance Test {i}",
            source=test_dirs['source'],
            dest=test_dirs['dest'],
            job_type=Job.TYPE_RSYNC
        )

    # Measure list_jobs performance
    start_time = time.time()
    jobs = job_manager.list_jobs()
    elapsed = time.time() - start_time

    print(f"\nlist_jobs with 50+ jobs took {elapsed*1000:.2f}ms")
    print(f"Retrieved {len(jobs)} jobs")

    # Should complete in reasonable time
    assert elapsed < 0.5, f"list_jobs took {elapsed:.3f}s, should be < 0.5s"
    assert len(jobs) >= 50


def test_cache_effectiveness_under_load(test_dirs, job_manager):
    """Test that caching improves performance under load."""
    # Create jobs
    for i in range(30):
        job_manager.create_job(
            name=f"Cache Test {i}",
            source=test_dirs['source'],
            dest=test_dirs['dest'],
            job_type=Job.TYPE_RSYNC
        )

    # First call (cache miss)
    start_time = time.time()
    jobs1 = job_manager.list_jobs()
    first_call = time.time() - start_time

    # Second call (cache hit)
    start_time = time.time()
    jobs2 = job_manager.list_jobs()
    second_call = time.time() - start_time

    print(f"\nFirst call (cache miss): {first_call*1000:.2f}ms")
    print(f"Second call (cache hit): {second_call*1000:.2f}ms")

    # Second call should be faster (cached)
    assert second_call < first_call, \
        f"Cache should improve performance. First: {first_call:.4f}s, Second: {second_call:.4f}s"


def test_concurrent_status_reads_under_load(test_dirs, job_manager):
    """Test concurrent status reads with many jobs."""
    # Create 30 jobs
    job_ids = []
    for i in range(30):
        success, msg, job = job_manager.create_job(
            name=f"Status Test {i}",
            source=test_dirs['source'],
            dest=test_dirs['dest'],
            job_type=Job.TYPE_RSYNC
        )
        if success:
            job_ids.append(job.id)

    # Read status from multiple threads
    read_count = [0]
    errors = []
    lock = threading.Lock()

    def read_statuses():
        try:
            for job_id in job_ids:
                status = job_manager.get_job_status(job_id)
                if status:
                    with lock:
                        read_count[0] += 1
        except Exception as e:
            with lock:
                errors.append(str(e))

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(read_statuses) for _ in range(10)]
        concurrent.futures.wait(futures)

    print(f"\nSuccessful status reads: {read_count[0]}")
    print(f"Errors: {len(errors)}")

    assert len(errors) == 0, f"Errors during concurrent reads: {errors[:3]}"
    assert read_count[0] >= 200, \
        f"Expected at least 200 successful reads, got {read_count[0]}"


def test_mixed_operations_under_load(test_dirs, job_manager):
    """Test mixed operations (create/start/stop/read) concurrently."""
    operation_counts = {
        'create': 0,
        'start': 0,
        'stop': 0,
        'read': 0,
        'delete': 0
    }
    errors = []
    lock = threading.Lock()
    job_ids_list = []

    def create_jobs():
        for i in range(10):
            try:
                success, msg, job = job_manager.create_job(
                    name=f"Mixed Op Job {i}",
                    source=test_dirs['source'],
                    dest=test_dirs['dest'],
                    job_type=Job.TYPE_RSYNC
                )
                if success:
                    with lock:
                        operation_counts['create'] += 1
                        job_ids_list.append(job.id)
            except Exception as e:
                with lock:
                    errors.append(f"Create: {str(e)}")

    def read_jobs():
        for _ in range(20):
            try:
                jobs = job_manager.list_jobs()
                with lock:
                    operation_counts['read'] += 1
                time.sleep(0.01)
            except Exception as e:
                with lock:
                    errors.append(f"Read: {str(e)}")

    def start_jobs():
        time.sleep(0.2)  # Wait for some jobs to be created
        with lock:
            ids_to_start = job_ids_list[:5]
        for job_id in ids_to_start:
            try:
                success, msg = job_manager.start_job(job_id)
                if success:
                    with lock:
                        operation_counts['start'] += 1
            except Exception as e:
                with lock:
                    errors.append(f"Start: {str(e)}")

    # Run mixed operations
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [
            executor.submit(create_jobs),
            executor.submit(create_jobs),
            executor.submit(read_jobs),
            executor.submit(read_jobs),
            executor.submit(start_jobs)
        ]
        concurrent.futures.wait(futures)

    print("\nOperation counts:")
    for op, count in operation_counts.items():
        print(f"  {op}: {count}")
    print(f"Errors: {len(errors)}")

    # Verify operations succeeded
    assert operation_counts['create'] >= 15, "Expected at least 15 successful creates"
    assert operation_counts['read'] >= 30, "Expected at least 30 successful reads"
    assert len(errors) < 5, f"Too many errors: {errors[:5]}"


def test_system_remains_responsive_under_load(test_dirs, job_manager):
    """Test that system remains responsive even under heavy load."""
    # Create 40 jobs rapidly
    start_time = time.time()

    job_ids = []
    for i in range(40):
        success, msg, job = job_manager.create_job(
            name=f"Responsiveness Test {i}",
            source=test_dirs['source'],
            dest=test_dirs['dest'],
            job_type=Job.TYPE_RSYNC
        )
        if success:
            job_ids.append(job.id)

    creation_time = time.time() - start_time

    # Test that reads remain fast
    start_time = time.time()
    jobs = job_manager.list_jobs()
    read_time = time.time() - start_time

    print(f"\nCreation time for 40 jobs: {creation_time:.2f}s")
    print(f"Read time with 40+ jobs: {read_time*1000:.2f}ms")

    # System should remain responsive
    assert read_time < 1.0, f"Read time {read_time:.3f}s exceeds 1s threshold"
    assert len(jobs) >= 40


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
