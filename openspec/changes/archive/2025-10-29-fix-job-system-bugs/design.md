## Context
The job system is the core of the backup manager, handling concurrent backup operations. Current implementation has thread safety issues, memory leaks, and UI synchronization problems that affect reliability and user experience.

## Goals / Non-Goals
- Goals:
  - Eliminate race conditions and data corruption
  - Prevent memory leaks
  - Ensure consistent UI state
  - Improve error visibility and recovery
  - Maintain backward compatibility

- Non-Goals:
  - Complete rewrite of job system
  - Migration to different storage format
  - Adding new job features
  - Changing job execution logic

## Decisions

### Decision: Separate Read and Write Operations
- get_job_status() becomes read-only, returns immutable data
- New update_job_from_engine() handles all state modifications
- Rationale: Prevents race conditions, follows command-query separation

### Decision: File Locking Strategy
- Use fcntl.flock() for YAML file locking
- Implement write queue with single writer thread
- Keep write locks brief (<100ms)
- Alternative considered: Database migration (too complex for bug fix)

### Decision: WebSocket Reconnection
```javascript
// Exponential backoff with jitter
let retries = 0;
let maxRetries = 10;
let baseDelay = 1000; // 1 second

function reconnect() {
    if (retries >= maxRetries) {
        showError("Connection lost. Please refresh page.");
        return;
    }
    
    let delay = Math.min(baseDelay * Math.pow(2, retries) + Math.random() * 1000, 30000);
    setTimeout(() => connectWebSocket(), delay);
    retries++;
}
```

### Decision: Engine Cleanup Policy
- Check engines every 10 seconds in background task
- Remove stopped engines after 30 seconds
- Remove failed engines immediately after status update
- Log all engine lifecycle events

### Decision: Progress Update Strategy
- Always save progress on status transition
- Buffer progress updates (max 1/second per job)
- Send final WebSocket message on completion
- Keep last 5 progress snapshots for recovery

## Risks / Trade-offs
- File locking may slow concurrent operations → Minimize lock duration
- WebSocket changes may affect existing clients → Backward compatible protocol
- Memory cleanup too aggressive → Keep recent completions for 5 minutes
- Breaking change in status query → Document clearly, version API

## Migration Plan
1. Deploy read/write separation with compatibility layer
2. Add file locking in parallel with existing writes
3. Update WebSocket clients progressively
4. Monitor for memory leaks and lock contention
5. Remove compatibility layer after validation

## Performance Targets
- Job status query: <10ms
- YAML write: <100ms with lock
- Memory usage: <10MB for 100 jobs
- WebSocket latency: <50ms
- Engine cleanup: within 30 seconds

## Error Recovery
- YAML corruption: Restore from backup (kept for 24 hours)
- WebSocket failure: Fallback to 5-second polling
- Engine crash: Mark job as failed, log details
- Lock timeout: Retry with exponential backoff
- Memory pressure: Force cleanup of old engines
