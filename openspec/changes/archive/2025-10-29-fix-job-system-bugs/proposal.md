## Why
The job system has critical bugs including race conditions in status updates, memory leaks with failed jobs, data corruption risks in YAML storage, and WebSocket reconnection loops that degrade user experience.

## What Changes
- Fix race condition in job status updates by separating read from write operations
- Implement automatic cleanup of stopped/failed engines to prevent memory leaks
- Add file locking for YAML storage to prevent concurrent write corruption
- Fix WebSocket reconnection with exponential backoff
- Ensure final progress is always saved on job completion
- Fix deletion checkbox state synchronization
- Prevent page reload on individual job completion
- Add proper error logging and user notifications
- **BREAKING**: Job status updates will no longer modify state during read operations

## Impact
- Affected specs: jobs-page, job-manager-thread-safety
- Affected code: core/job_manager.py, storage/job_storage.py, fastapi_app/background.py, fastapi_app/templates/jobs.html, fastapi_app/websocket/manager.py
