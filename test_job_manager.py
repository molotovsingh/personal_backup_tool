"""Test JobManager functionality"""
import time
import tempfile
import shutil
from pathlib import Path
from core.job_manager import JobManager
from storage.job_storage import JobStorage

# Set up temp directories for testing
temp_base = tempfile.mkdtemp()
test_source = Path(temp_base) / "source"
test_dest = Path(temp_base) / "dest"
test_source.mkdir()
test_dest.mkdir()

# Create some test files
(test_source / "test1.txt").write_text("Hello World")
(test_source / "test2.txt").write_text("Test Data" * 100)

print(f"Test directories: {test_source} -> {test_dest}")

# Test 1: Singleton pattern
print("\nTest 1: Singleton pattern...")
manager1 = JobManager()
manager2 = JobManager()
assert manager1 is manager2, "Should return same instance"
print("✓ Singleton enforced")

# Test 2: Create job
print("\nTest 2: Create job...")
success, msg, job = manager1.create_job(
    name="Test Backup",
    source=str(test_source),
    dest=str(test_dest),
    job_type="rsync",
    settings={'bandwidth_limit': 1000}
)
assert success == True, f"Create should succeed: {msg}"
assert job is not None, "Should return job instance"
print(f"✓ Created job: {job.id}")
job_id = job.id

# Test 3: List jobs
print("\nTest 3: List jobs...")
jobs = manager1.list_jobs()
assert len(jobs) >= 1, "Should have at least 1 job"
assert any(j['id'] == job_id for j in jobs), "Should find our job"
print(f"✓ Listed {len(jobs)} job(s)")

# Test 4: Get job status
print("\nTest 4: Get job status...")
status = manager1.get_job_status(job_id)
assert status is not None, "Should get status"
assert status['status'] == 'pending', f"Should be pending, got {status['status']}"
print(f"✓ Status: {status['status']}")

# Test 5: Start job
print("\nTest 5: Start job...")
success, msg = manager1.start_job(job_id)
assert success == True, f"Start should succeed: {msg}"
print(f"✓ {msg}")

# Verify job is running
status = manager1.get_job_status(job_id)
assert status['status'] == 'running', f"Should be running, got {status['status']}"
print(f"✓ Job is running")

# Test 6: Prevent starting same job twice
print("\nTest 6: Prevent duplicate start...")
success, msg = manager1.start_job(job_id)
assert success == False, "Should not allow duplicate start"
assert "already running" in msg.lower(), f"Wrong error message: {msg}"
print(f"✓ Duplicate start prevented: {msg}")

# Test 7: Engine tracking
print("\nTest 7: Engine tracking...")
assert job_id in manager1.engines, "Engine should be tracked"
assert manager1.engines[job_id].is_running(), "Engine should be running"
print(f"✓ Engine tracked in memory")

# Let it run a bit
print("\nWaiting 2 seconds for progress...")
time.sleep(2)

# Check progress
status = manager1.get_job_status(job_id)
print(f"Progress: {status['progress']}")

# Test 8: Stop job (or verify already completed)
print("\nTest 8: Stop job (or check if already completed)...")
# Check if job already completed
status = manager1.get_job_status(job_id)
if status['status'] == 'completed':
    print(f"✓ Job already completed (was too fast!)")
elif job_id in manager1.engines:
    success, msg = manager1.stop_job(job_id)
    assert success == True, f"Stop should succeed: {msg}"
    print(f"✓ {msg}")
    status = manager1.get_job_status(job_id)
    assert status['status'] in ['paused', 'completed'], f"Should be paused/completed, got {status['status']}"
    print(f"✓ Job stopped, status: {status['status']}")
else:
    print(f"✓ Job finished and engine auto-cleaned: {status['status']}")

# Test 9: Engine cleanup
print("\nTest 9: Engine cleanup...")
assert job_id not in manager1.engines, "Engine should be removed from memory"
print(f"✓ Engine cleaned up")

# Test 10: Delete job
print("\nTest 10: Delete job...")
success, msg = manager1.delete_job(job_id)
assert success == True, f"Delete should succeed: {msg}"
print(f"✓ {msg}")

# Verify deletion
jobs = manager1.list_jobs()
assert not any(j['id'] == job_id for j in jobs), "Job should be deleted"
print(f"✓ Job removed from storage")

# Cleanup
shutil.rmtree(temp_base)
print(f"\n✓ Cleaned up test directory: {temp_base}")

# Clean up jobs.yaml if it was created
jobs_yaml = Path.home() / 'backup-manager' / 'jobs.yaml'
if jobs_yaml.exists():
    JobStorage().clear_all()
    print("✓ Cleaned up jobs.yaml")

print("\n✓✓✓ All JobManager tests passed!")
