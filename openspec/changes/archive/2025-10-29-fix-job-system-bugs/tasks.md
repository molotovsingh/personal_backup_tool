## 1. Fix Critical Race Conditions
- [x] 1.1 Separate get_job_status() into read-only operation
- [x] 1.2 Create update_job_from_engine() method for state modifications
- [x] 1.3 Fix lock ordering between main lock and engines lock
- [x] 1.4 Ensure atomic state transitions for job status
- [x] 1.5 Add version/timestamp checking for concurrent updates

## 2. Fix Memory Leaks
- [x] 2.1 Implement periodic engine cleanup task
- [x] 2.2 Call cleanup_stopped_engines() from background monitor
- [x] 2.3 Add engine lifecycle logging for debugging
- [x] 2.4 Ensure engines removed on all failure paths
- [x] 2.5 Add max engine retention time (5 minutes after stop)

## 3. Fix Data Storage Issues
- [x] 3.1 Add file locking to YAML write operations
- [x] 3.2 Implement write queue for serialized updates
- [x] 3.3 Add corruption detection and recovery
- [x] 3.4 Ensure final progress always saved before status change
- [x] 3.5 Add backup copies of jobs.yaml before writes

## 4. Fix WebSocket Issues
- [x] 4.1 Implement exponential backoff for reconnection
- [x] 4.2 Add max retry limit (10 attempts)
- [x] 4.3 Show connection status indicator in UI
- [x] 4.4 Fallback to polling if WebSocket fails
- [x] 4.5 Prevent page reload on individual job completion

## 5. Fix UI State Management
- [x] 5.1 Synchronize deletion checkbox with options panel
- [x] 5.2 Preserve form state during HTMX updates
- [x] 5.3 Update only affected job cards (not full reload)
- [x] 5.4 Maintain scroll position on updates
- [x] 5.5 Add loading indicators for async operations

## 6. Improve Error Handling
- [x] 6.1 Replace print() with proper logging
- [x] 6.2 Add user notifications for background failures
- [x] 6.3 Implement error recovery strategies
- [x] 6.4 Add health check endpoint for monitoring
- [x] 6.5 Create error event log in database

## 7. Optimize Performance
- [x] 7.1 Cache job list for 1 second (dirty checking)
- [x] 7.2 Only poll when jobs are running
- [x] 7.3 Batch WebSocket updates (max 10/second)
- [x] 7.4 Use read-write lock instead of single lock (implemented with custom ReadWriteLock)
- [x] 7.5 Lazy load job details on expansion (implemented with HTMX lazy loading)

## 8. Testing
- [x] 8.1 Test concurrent job operations (start/stop/status)
- [x] 8.2 Test WebSocket reconnection scenarios
- [x] 8.3 Verify no memory leaks after 100 job cycles
- [x] 8.4 Test YAML corruption recovery
- [x] 8.5 Load test with 50+ concurrent jobs
- [x] 8.6 Test UI state preservation across updates
