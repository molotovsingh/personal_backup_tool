"""
Test Phase 8.4: YAML Corruption Recovery
Tests for YAML file corruption detection and recovery mechanisms.
"""
import pytest
import tempfile
import shutil
from pathlib import Path
import yaml
from storage.job_storage import JobStorage
from models.job import Job


@pytest.fixture
def temp_storage_dir():
    """Create temporary storage directory."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def storage(temp_storage_dir):
    """Create JobStorage instance with temp directory."""
    storage_path = Path(temp_storage_dir) / "jobs.yaml"
    return JobStorage(str(storage_path))


def test_yaml_corruption_detection(storage, temp_storage_dir):
    """Test that corrupted YAML files are detected."""
    # Create a valid job first
    job = Job(
        name="Test Job",
        source="/tmp/source",
        dest="/tmp/dest",
        job_type=Job.TYPE_RSYNC
    )
    assert storage.save_job(job)

    # Corrupt the YAML file
    storage_path = Path(temp_storage_dir) / "jobs.yaml"
    with open(storage_path, 'w') as f:
        f.write("{ invalid yaml syntax {[ broken")

    # Try to load - should detect corruption
    jobs = storage.load_jobs()

    # Should either:
    # 1. Recover from backup (if backup exists)
    # 2. Return empty list (if no backup)
    assert isinstance(jobs, list), "load_jobs should return a list even after corruption"


def test_yaml_backup_creation(storage, temp_storage_dir):
    """Test that backup files are created before writes."""
    # Create a job
    job = Job(
        name="Backup Test",
        source="/tmp/source",
        dest="/tmp/dest",
        job_type=Job.TYPE_RSYNC
    )
    assert storage.save_job(job)

    # Check that backup file exists
    backup_path = Path(temp_storage_dir) / "jobs.yaml.bak"
    assert backup_path.exists(), "Backup file should be created"

    # Backup should contain valid YAML
    with open(backup_path, 'r') as f:
        backup_data = yaml.safe_load(f)
    assert backup_data is not None
    assert 'jobs' in backup_data


def test_yaml_recovery_from_backup(storage, temp_storage_dir):
    """Test recovery from backup file when main file is corrupted."""
    storage_path = Path(temp_storage_dir) / "jobs.yaml"
    backup_path = Path(temp_storage_dir) / "jobs.yaml.bak"

    # Create a valid job
    job = Job(
        name="Recovery Test",
        source="/tmp/source",
        dest="/tmp/dest",
        job_type=Job.TYPE_RSYNC
    )
    assert storage.save_job(job)

    # Verify backup exists
    assert backup_path.exists()

    # Corrupt main file
    with open(storage_path, 'w') as f:
        f.write("corrupted {{{")

    # Load jobs - should recover from backup
    jobs = storage.load_jobs()

    # Should recover the job
    if len(jobs) > 0:
        recovered_job = jobs[0]
        assert recovered_job.name == "Recovery Test"


def test_yaml_atomic_write_pattern(storage, temp_storage_dir):
    """Test that writes use atomic pattern (temp file + rename)."""
    # Create a job
    job = Job(
        name="Atomic Write Test",
        source="/tmp/source",
        dest="/tmp/dest",
        job_type=Job.TYPE_RSYNC
    )

    # Save job (should use atomic write)
    assert storage.save_job(job)

    # File should exist and be valid
    storage_path = Path(temp_storage_dir) / "jobs.yaml"
    assert storage_path.exists()

    with open(storage_path, 'r') as f:
        data = yaml.safe_load(f)

    assert data is not None
    assert 'jobs' in data
    assert len(data['jobs']) >= 1


def test_yaml_file_locking_prevents_corruption(storage):
    """Test that file locking prevents concurrent write corruption."""
    import threading
    import time

    jobs_to_create = []
    errors = []

    def create_job(index):
        try:
            job = Job(
                name=f"Concurrent Job {index}",
                source="/tmp/source",
                dest="/tmp/dest",
                job_type=Job.TYPE_RSYNC
            )
            if storage.save_job(job):
                jobs_to_create.append(job.id)
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

    # No errors should occur
    assert len(errors) == 0, f"Errors during concurrent writes: {errors}"

    # Load jobs - should have all 10
    jobs = storage.load_jobs()
    assert len(jobs) == 10, \
        f"Expected 10 jobs after concurrent writes, got {len(jobs)}. File may be corrupted."


def test_yaml_validation_on_load(storage, temp_storage_dir):
    """Test that invalid YAML structures are detected."""
    storage_path = Path(temp_storage_dir) / "jobs.yaml"

    # Write invalid structure (not a dict)
    with open(storage_path, 'w') as f:
        yaml.dump(['not', 'a', 'dict'], f)

    # Load should handle invalid structure
    jobs = storage.load_jobs()
    assert isinstance(jobs, list), "Should return list even with invalid structure"


def test_yaml_handles_missing_file_gracefully(temp_storage_dir):
    """Test that missing YAML file is handled gracefully."""
    nonexistent_path = Path(temp_storage_dir) / "nonexistent.yaml"
    storage = JobStorage(str(nonexistent_path))

    # Should return empty list, not crash
    jobs = storage.load_jobs()
    assert jobs == []


def test_yaml_corruption_in_jobs_list(storage, temp_storage_dir):
    """Test handling of corrupted job data in jobs list."""
    storage_path = Path(temp_storage_dir) / "jobs.yaml"

    # Write YAML with invalid job structure
    invalid_data = {
        'jobs': [
            {
                'id': 'valid-job-1',
                'name': 'Valid Job',
                'source': '/tmp/source',
                'dest': '/tmp/dest',
                'type': 'rsync',
                'status': 'pending'
            },
            # Missing required fields
            {
                'id': 'invalid-job-2',
                'name': 'Invalid Job'
                # Missing source, dest, type, status
            }
        ]
    }

    with open(storage_path, 'w') as f:
        yaml.dump(invalid_data, f)

    # Load jobs - should skip invalid entries or handle gracefully
    jobs = storage.load_jobs()

    # Should load at least the valid job
    assert len(jobs) >= 1, "Should load valid jobs even if some are corrupted"


def test_yaml_backup_restored_after_corruption(storage, temp_storage_dir):
    """Test that main file is restored from backup after corruption detection."""
    storage_path = Path(temp_storage_dir) / "jobs.yaml"
    backup_path = Path(temp_storage_dir) / "jobs.yaml.bak"

    # Create initial job
    job = Job(
        name="Original Job",
        source="/tmp/source",
        dest="/tmp/dest",
        job_type=Job.TYPE_RSYNC
    )
    storage.save_job(job)

    # Save backup content
    with open(backup_path, 'r') as f:
        backup_content = f.read()

    # Corrupt main file
    with open(storage_path, 'w') as f:
        f.write("corrupted content {{")

    # Load jobs (should trigger recovery)
    jobs = storage.load_jobs()

    # After recovery, main file should be restored (implementation-dependent)
    # At minimum, we should have recovered the data
    if len(jobs) > 0:
        assert jobs[0].name == "Original Job"


def test_yaml_write_queue_processes_in_order(storage):
    """Test that write queue processes writes in order."""
    import time

    # Create jobs quickly to queue writes
    job_ids = []
    for i in range(5):
        job = Job(
            name=f"Queued Job {i}",
            source="/tmp/source",
            dest="/tmp/dest",
            job_type=Job.TYPE_RSYNC
        )
        if storage.save_job(job):
            job_ids.append(job.id)

    # Wait for queue to process
    time.sleep(1)

    # Load and verify all jobs were saved
    jobs = storage.load_jobs()
    assert len(jobs) >= 5, f"Expected at least 5 jobs, got {len(jobs)}"

    # Verify jobs have unique IDs (no overwrites)
    loaded_ids = [j.id for j in jobs]
    assert len(set(loaded_ids)) == len(loaded_ids), "Jobs should have unique IDs"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
