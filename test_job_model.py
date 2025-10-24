"""Quick test for Job model"""
from models.job import Job

# Test 1: Create a job
print("Test 1: Creating a job...")
job = Job(
    name="Test Backup",
    source="/tmp/source",
    dest="/tmp/dest",
    job_type="rsync",
    settings={'bandwidth_limit': 5000}
)
print(f"✓ Created: {job}")

# Test 2: Convert to dict
print("\nTest 2: Converting to dict...")
job_dict = job.to_dict()
print(f"✓ Dict keys: {list(job_dict.keys())}")
assert all(key in job_dict for key in ['id', 'name', 'source', 'dest', 'type', 'status', 'progress', 'settings', 'created_at', 'updated_at'])
print("✓ All required fields present")

# Test 3: Create from dict
print("\nTest 3: Creating from dict...")
job2 = Job.from_dict(job_dict)
print(f"✓ Recreated: {job2}")
assert job2.id == job.id
assert job2.name == job.name
print("✓ Data preserved")

# Test 4: Update progress
print("\nTest 4: Updating progress...")
job.update_progress({'percent': 50, 'bytes_transferred': 1000000})
assert job.progress['percent'] == 50
print(f"✓ Progress updated: {job.progress['percent']}%")

# Test 5: Update status
print("\nTest 5: Updating status...")
job.update_status('running')
assert job.status == 'running'
print(f"✓ Status updated: {job.status}")

# Test 6: Validation errors
print("\nTest 6: Testing validation...")
try:
    bad_job = Job(name="", source="", dest="", job_type="invalid")
    print("✗ Should have raised ValueError")
except ValueError as e:
    print(f"✓ Validation error caught: {str(e)[:50]}...")

print("\n✓✓✓ All tests passed!")
