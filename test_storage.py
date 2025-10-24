"""Test JobStorage functionality"""
import tempfile
from pathlib import Path
from storage.job_storage import JobStorage
from models.job import Job

# Use temporary directory for testing
temp_dir = tempfile.mkdtemp()
test_storage_path = Path(temp_dir) / "test_jobs.yaml"
print(f"Testing with: {test_storage_path}")

# Test 1: Initialize storage
print("\nTest 1: Initialize storage...")
storage = JobStorage(str(test_storage_path))
assert test_storage_path.exists(), "Storage file should be created"
print(f"✓ Created: {test_storage_path}")

# Test 2: Save a job
print("\nTest 2: Save a job...")
job1 = Job(name="Job 1", source="/tmp/src1", dest="/tmp/dst1", job_type="rsync")
result = storage.save_job(job1)
assert result == True, "Save should return True"
print(f"✓ Saved job: {job1.id}")

# Test 3: Load jobs
print("\nTest 3: Load jobs...")
jobs = storage.load_jobs()
assert len(jobs) == 1, f"Should have 1 job, got {len(jobs)}"
assert jobs[0].id == job1.id, "Job ID should match"
assert jobs[0].name == "Job 1", "Job name should match"
print(f"✓ Loaded {len(jobs)} job(s)")

# Test 4: Save multiple jobs
print("\nTest 4: Save multiple jobs...")
job2 = Job(name="Job 2", source="/tmp/src2", dest="/tmp/dst2", job_type="rclone")
job3 = Job(name="Job 3", source="/tmp/src3", dest="/tmp/dst3", job_type="rsync")
storage.save_job(job2)
storage.save_job(job3)
jobs = storage.load_jobs()
assert len(jobs) == 3, f"Should have 3 jobs, got {len(jobs)}"
print(f"✓ Saved and loaded {len(jobs)} jobs")

# Test 5: Get specific job
print("\nTest 5: Get specific job...")
retrieved_job = storage.get_job(job2.id)
assert retrieved_job is not None, "Should find job"
assert retrieved_job.name == "Job 2", "Should get correct job"
print(f"✓ Retrieved job: {retrieved_job.name}")

# Test 6: Update job
print("\nTest 6: Update job...")
job1.update_status('running')
job1.update_progress({'percent': 75})
result = storage.update_job(job1)
assert result == True, "Update should return True"
retrieved = storage.get_job(job1.id)
assert retrieved.status == 'running', "Status should be updated"
assert retrieved.progress['percent'] == 75, "Progress should be updated"
print(f"✓ Updated job status: {retrieved.status}, progress: {retrieved.progress['percent']}%")

# Test 7: Delete job
print("\nTest 7: Delete job...")
result = storage.delete_job(job2.id)
assert result == True, "Delete should return True"
jobs = storage.load_jobs()
assert len(jobs) == 2, f"Should have 2 jobs after delete, got {len(jobs)}"
assert all(j.id != job2.id for j in jobs), "Deleted job should not be in list"
print(f"✓ Deleted job, {len(jobs)} remaining")

# Test 8: Count jobs
print("\nTest 8: Count jobs...")
count = storage.count_jobs()
assert count == 2, f"Count should be 2, got {count}"
print(f"✓ Job count: {count}")

# Test 9: Clear all
print("\nTest 9: Clear all jobs...")
result = storage.clear_all()
assert result == True, "Clear should return True"
jobs = storage.load_jobs()
assert len(jobs) == 0, "Should have 0 jobs after clear"
print(f"✓ Cleared all jobs")

# Test 10: Handle empty file
print("\nTest 10: Load from empty storage...")
jobs = storage.load_jobs()
assert jobs == [], "Should return empty list"
print(f"✓ Handles empty storage gracefully")

# Cleanup
import shutil
shutil.rmtree(temp_dir)
print(f"\n✓ Cleaned up test directory: {temp_dir}")

print("\n✓✓✓ All storage tests passed!")
