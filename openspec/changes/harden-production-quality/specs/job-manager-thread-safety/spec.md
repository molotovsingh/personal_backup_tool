# Spec: Job Manager Thread Safety

## Summary
Add proper threading locks for job list iteration in JobManager to prevent race conditions during concurrent access from Flask request threads and WebSocket update threads.

## MODIFIED Requirements

### Requirement: Job list operations SHALL use thread-safe locking
The system SHALL protect all job list read and write operations with threading.Lock to prevent concurrent modification issues.

#### Scenario: Concurrent job list access is thread-safe
```python
# Given: JobManager with 10 active jobs
manager = JobManager()
for i in range(10):
    manager.create_job(f'job_{i}', '/src', '/dest', 'rsync')

# When: Multiple threads access job list concurrently
import threading
errors = []

def read_jobs():
    try:
        for _ in range(100):
            jobs = manager.list_jobs()
            assert isinstance(jobs, list)
    except Exception as e:
        errors.append(e)

def update_job():
    try:
        for i in range(100):
            manager.update_job_progress('job_0', {'percent': i % 100})
    except Exception as e:
        errors.append(e)

# Create 10 reader threads and 5 writer threads
threads = []
for _ in range(10):
    threads.append(threading.Thread(target=read_jobs))
for _ in range(5):
    threads.append(threading.Thread(target=update_job))

# Start all threads
for t in threads:
    t.start()

# Wait for completion
for t in threads:
    t.join()

# Then: No race condition errors occur
assert len(errors) == 0
```

#### Scenario: Job cleanup during iteration is safe
```python
# Given: JobManager with cleanup thread running
manager = JobManager()
cleanup_running = True

def cleanup_thread():
    while cleanup_running:
        # Attempts to clean up old jobs during iteration
        manager._cleanup_completed_jobs()
        time.sleep(0.1)

cleanup = threading.Thread(target=cleanup_thread)
cleanup.start()

# When: Main thread iterates over jobs
errors = []
try:
    for _ in range(100):
        jobs = manager.list_jobs()
        for job in jobs:
            # Simulate work with each job
            status = job.get('status')
except Exception as e:
    errors.append(e)

cleanup_running = False
cleanup.join()

# Then: No "dictionary changed size during iteration" errors
assert len(errors) == 0
```

### Requirement: Lock SHALL protect storage operations
The system SHALL use the same lock for both in-memory job list operations and storage persistence to ensure consistency.

#### Scenario: Job update and save are atomic
```python
# Given: JobManager with a job
manager = JobManager()
job_id = manager.create_job('test', '/src', '/dest', 'rsync')

# When: Multiple threads update the same job
def update_progress(percent):
    manager.update_job_progress(job_id, {'percent': percent})

threads = [threading.Thread(target=update_progress, args=(i,)) for i in range(100)]
for t in threads:
    t.start()
for t in threads:
    t.join()

# Then: Job has one of the progress values (not corrupted)
job = manager.get_job(job_id)
assert 0 <= job['progress']['percent'] <= 100

# And: Saved job matches in-memory job
manager.storage.load_jobs()  # Reload from disk
saved_job = manager.get_job(job_id)
assert saved_job['progress']['percent'] == job['progress']['percent']
```

## ADDED Requirements

### Requirement: Locking SHALL not cause deadlocks
The system SHALL use a single, consistently ordered lock to prevent deadlock scenarios.

#### Scenario: Nested operations do not deadlock
```python
# Given: JobManager with reentrant lock or careful lock ordering
manager = JobManager()
job_id = manager.create_job('test', '/src', '/dest', 'rsync')

# When: Method calls other methods that also acquire lock
# (e.g., update_job_progress calls _save_jobs which also needs lock)
def nested_update():
    manager.update_job_progress(job_id, {'percent': 50})

# Then: Operation completes without deadlock
import threading
t = threading.Thread(target=nested_update)
t.start()
t.join(timeout=2)  # Wait max 2 seconds

# Thread should complete
assert not t.is_alive()
```

### Requirement: Lock acquisition SHALL have timeout
The system SHALL use lock.acquire(timeout=X) to prevent indefinite blocking in case of bugs.

#### Scenario: Lock acquisition timeout prevents hanging
```python
# Given: JobManager with lock timeout configured
manager = JobManager()

# When: Lock is held by another thread for too long
import threading
lock_acquired = threading.Event()
lock_released = threading.Event()

def hold_lock():
    with manager._lock:
        lock_acquired.set()
        lock_released.wait()  # Hold until signaled

holder = threading.Thread(target=hold_lock)
holder.start()
lock_acquired.wait()  # Wait for lock to be held

# Attempt operation that needs lock
try:
    # This should timeout rather than hang forever
    manager.list_jobs()  # Will attempt lock.acquire(timeout=5)
    result = "succeeded"
except TimeoutError:
    result = "timeout"

# Then: Operation either succeeds or times out (doesn't hang)
assert result in ["succeeded", "timeout"]

# Cleanup
lock_released.set()
holder.join()
```
