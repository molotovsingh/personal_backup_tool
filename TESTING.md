# End-to-End Testing Guide

## Test Suite for Backup Manager

### Prerequisites
- [ ] rsync installed (`which rsync`)
- [ ] rclone installed (`brew install rclone`) [optional for cloud tests]
- [ ] Virtual environment set up (`uv venv` completed)
- [ ] Dependencies installed (`uv pip install -r requirements.txt`)

---

## Test 1: Basic Job Creation & Execution (rsync)

**Goal**: Verify basic rsync job creation and execution

**Steps**:
1. Create test directories:
   ```bash
   mkdir -p ~/test_backup/source
   mkdir -p ~/test_backup/dest
   echo "Test file 1" > ~/test_backup/source/file1.txt
   echo "Test file 2" > ~/test_backup/source/file2.txt
   ```

2. Run the app: `uv run uvicorn fastapi_app:app --host 0.0.0.0 --port 5001 --reload`

3. Navigate to **Jobs** page

4. Click **"➕ New Job"**

5. Fill in the form:
   - Name: "Test Rsync Backup"
   - Type: rsync
   - Source: `/Users/<your-username>/test_backup/source`
   - Destination: `/Users/<your-username>/test_backup/dest`

6. Click **"Create Job"**

**Expected Results**:
- [ ] Success message appears
- [ ] Job appears in job list with "pending" status
- [ ] Job ID is shown

7. Click **"▶️ Start"** button

**Expected Results**:
- [ ] Status changes to "running"
- [ ] Progress bar appears and updates
- [ ] Files transfer successfully
- [ ] Status changes to "completed"
- [ ] Check destination folder has the files

---

## Test 2: Progress Monitoring

**Goal**: Verify real-time progress tracking

**Steps**:
1. Create a larger test file:
   ```bash
   dd if=/dev/zero of=~/test_backup/source/large.dat bs=1m count=100
   ```

2. Start the job from Test 1

3. Navigate to **Dashboard**

**Expected Results**:
- [ ] Active Jobs panel shows the running job
- [ ] Progress bar updates in real-time
- [ ] Speed (MB/s) is displayed
- [ ] ETA is calculated
- [ ] Bytes transferred increases
- [ ] Auto-refresh works (dashboard updates every 2s)

---

## Test 3: Stop/Resume Job

**Goal**: Verify pause and resume functionality

**Steps**:
1. Start a large transfer (from Test 2)

2. Click **"⏸️ Stop"** when progress reaches ~50%

**Expected Results**:
- [ ] Status changes to "paused"
- [ ] Process stops
- [ ] Progress is saved

3. Click **"▶️ Start"** again

**Expected Results**:
- [ ] Job resumes from where it stopped
- [ ] Progress continues from previous point (not from 0%)
- [ ] Transfer completes successfully

---

## Test 4: Job Deletion

**Goal**: Verify job deletion with confirmation

**Steps**:
1. Create a test job

2. Click **"🗑️ Delete"**

**Expected Results**:
- [ ] Warning message appears asking for confirmation

3. Click **"🗑️ Delete"** again

**Expected Results**:
- [ ] Job is removed from list
- [ ] Success message appears
- [ ] Job removed from `~/backup-manager/jobs.yaml`

---

## Test 5: Crash Recovery

**Goal**: Verify app restart recovery

**Steps**:
1. Start a long-running job

2. Kill the app (Ctrl+C or close browser)

3. Restart the app: `uv run uvicorn fastapi_app:app --host 0.0.0.0 --port 5001 --reload`

**Expected Results**:
- [ ] Sidebar shows warning: "⚠️ 1 interrupted job(s) found"
- [ ] "Resume Interrupted Jobs" button appears
- [ ] Click "Resume" button
- [ ] Jobs marked as "paused"
- [ ] Can manually restart them

---

## Test 6: Network Failure & Auto-Reconnect

**Goal**: Verify automatic retry on network failure

**Steps**:
1. Start a network transfer job (to network share or remote)

2. Disconnect network (turn off WiFi or unplug ethernet)

3. Wait 10 seconds

4. Reconnect network

5. Check logs: `cat ~/backup-manager/logs/rsync_*.log | grep -i retry`

**Expected Results**:
- [ ] Logs show "network error" detected
- [ ] Logs show retry attempts with backoff (1s, 2s, 4s, 8s...)
- [ ] Transfer resumes automatically after network restored
- [ ] Status shows "running (retrying...)" during retry
- [ ] Transfer completes successfully

---

## Test 7: Rclone Job (Cloud Storage)

**Goal**: Verify rclone integration for cloud backups

**Prerequisites**:
- [ ] rclone installed
- [ ] rclone remote configured (`rclone config`)

**Steps**:
1. Navigate to **Jobs** page

2. Click **"➕ New Job"**

3. Fill in the form:
   - Name: "Test Cloud Backup"
   - Type: rclone
   - Source: `/Users/<your-username>/test_backup/source`
   - Select configured remote from dropdown
   - Remote path: `test_backup`

4. Click **"Create Job"**

5. Click **"▶️ Start"**

**Expected Results**:
- [ ] Job starts successfully
- [ ] Files upload to cloud storage
- [ ] Progress is tracked
- [ ] Job completes
- [ ] Verify files in cloud storage (check via rclone or web interface)

---

## Test 8: Settings Persistence

**Goal**: Verify settings are saved and applied

**Steps**:
1. Navigate to **Settings** page

2. Change settings:
   - Default Bandwidth: 5000 KB/s
   - Auto-start on launch: checked
   - Network check interval: 60 seconds

3. Click **"💾 Save Settings"**

4. Close and restart the app

5. Navigate to **Settings** page

**Expected Results**:
- [ ] All settings are preserved
- [ ] Check `~/backup-manager/settings.yaml` contains values

---

## Test 9: Log Filtering & Export

**Goal**: Verify log viewer functionality

**Steps**:
1. Run several jobs to generate logs

2. Navigate to **Logs** page

3. Select a specific job from dropdown

4. Search for "completed"

5. Click **"📥 Export"**

**Expected Results**:
- [ ] Logs are filtered to selected job
- [ ] Search highlights matching lines
- [ ] Export downloads a .txt file with filtered logs
- [ ] File contains only the filtered log entries

---

## Test 10: Disk Space Validation

**Goal**: Verify pre-start disk space checking

**Steps**:
1. Create a test job with destination on a nearly-full disk

2. Try to start the job

**Expected Results**:
- [ ] If <10% space available, shows error
- [ ] Error message indicates low disk space
- [ ] Job does not start
- [ ] User-friendly error message displayed

---

## Test 11: Large File Resume

**Goal**: Verify resume works for large files

**Steps**:
1. Create a 1GB test file:
   ```bash
   dd if=/dev/zero of=~/test_backup/source/large1gb.dat bs=1m count=1024
   ```

2. Start transfer

3. Stop job at 40%

4. Restart job

**Expected Results**:
- [ ] Transfer resumes from 40% (not from 0%)
- [ ] Log shows "--partial" and "--append-verify" flags
- [ ] Completes successfully
- [ ] Final file size matches source

---

## Cleanup

After testing:

```bash
# Remove test data
rm -rf ~/test_backup

# Optional: Clean up app data
rm -rf ~/backup-manager
```

---

## Critical Bug Fixes (2025-10-29)

This section documents critical stability and reliability fixes implemented to address race conditions, memory leaks, file corruption, and WebSocket issues.

### Phase 1: Race Condition Fixes

**Issue**: `get_job_status()` was both reading AND modifying job state, causing concurrent modification issues.

**Fix Applied** (core/job_manager.py):
- Separated read and write operations using Command-Query Separation principle
- `get_job_status()` is now strictly read-only (lines 250-296)
- New `update_job_from_engine()` handles all state modifications (lines 298-364)
- Proper lock ordering: main lock → engines lock

**Test Verification**:
1. Start multiple jobs simultaneously
2. Monitor logs for "Error getting job status" messages
3. Expected: No race condition errors, clean state transitions

### Phase 2: Memory Leak Fixes

**Issue**: Stopped engines remained in memory indefinitely, causing memory leaks over time.

**Fix Applied** (core/job_manager.py + fastapi_app/background.py):
- Added `cleanup_stopped_engines()` method (lines 366-397)
- Integrated into background monitoring task
- Runs every 10 seconds to clean up stopped engines
- Proper lifecycle logging

**Test Verification**:
1. Start and complete several jobs
2. Check server logs for "Cleaned up X stopped engine(s)"
3. Monitor memory usage over time
4. Expected: Memory remains stable, engines are cleaned up

### Phase 3: File Corruption Prevention

**Issue**: Concurrent YAML writes could corrupt jobs.yaml file.

**Fix Applied** (storage/job_storage.py):
- Added fcntl.flock() exclusive locking (lines 207-231)
- Backup creation before writes (.bak file)
- Atomic write pattern (temp file + rename)
- Proper lock release in finally block

**Test Verification**:
1. Create/update multiple jobs rapidly from different browser tabs
2. Check jobs.yaml integrity: `cat ~/backup-manager/jobs.yaml`
3. Check for backup file: `ls -l ~/backup-manager/jobs.yaml.bak`
4. Expected: No corruption, valid YAML structure maintained

### Phase 4: WebSocket Reliability

**Issue**: Page reloaded on WebSocket disconnect, poor user experience, no reconnection logic.

**Fix Applied** (fastapi_app/templates/jobs.html + dashboard.html):
- Exponential backoff reconnection (1s → 2s → 4s → 8s... up to 30s)
- Maximum retry limit (10 attempts)
- Connection status indicator (top-right corner)
- Fallback to HTMX polling after max retries (jobs page only)
- HTMX refresh instead of full page reload on job completion
- Jitter added to prevent thundering herd

**Test Verification**:
1. Start the app and navigate to Jobs page
2. Observe connection status indicator (green "● Connected", fades after 3s)
3. Stop the backend server
4. Expected: Yellow "● Reconnecting... (attempt X/10)" appears
5. Wait through several retry attempts
6. Restart server
7. Expected: Reconnects automatically, green indicator shows briefly
8. Alternative: Let it reach max retries (10)
9. Expected (jobs page): Blue "● Using fallback polling" - page updates every 5s
10. Expected (dashboard): Red "● Disconnected - Refresh to reconnect"

**WebSocket Reconnection Behavior**:
- Attempt 1: ~1s delay
- Attempt 2: ~2s delay
- Attempt 3: ~4s delay
- Attempt 4: ~8s delay
- Attempt 5: ~16s delay
- Attempts 6-10: 30s delay (capped)
- After 10 failed attempts (jobs page): Enable polling fallback
- After 10 failed attempts (dashboard): Manual refresh required

### Additional Improvements

**Background Monitoring** (fastapi_app/background.py):
- Periodic engine cleanup every 10 seconds
- Job state updates from engines every 1 second
- Final state detection and broadcasting

**Startup Recovery** (fastapi_app/__init__.py):
- Automatic detection of zombie jobs (marked "running" but no engine)
- Jobs marked as "paused" on server restart
- User notification of interrupted jobs

---

## Test 12: Health Check Endpoint

**Goal**: Verify health monitoring endpoint

**Steps**:
1. Start the app

2. Navigate to http://localhost:5001/health or use curl:
   ```bash
   curl -s http://localhost:5001/health | python3 -m json.tool
   ```

**Expected Results**:
- [ ] Returns JSON with overall status ("healthy", "degraded", or "unhealthy")
- [ ] Shows storage component status with job count
- [ ] Shows background tasks status with log_indexer status
- [ ] Shows job_engines status with total and running engine counts
- [ ] Shows logs directory status
- [ ] All healthy components show "healthy" status
- [ ] Overall status is "healthy" when all components are operational

**Example healthy response**:
```json
{
    "status": "healthy",
    "timestamp": "2025-10-29T09:50:16.344894",
    "components": {
        "storage": {
            "status": "healthy",
            "job_count": 0
        },
        "background_tasks": {
            "status": "healthy",
            "log_indexer": "running"
        },
        "job_engines": {
            "status": "healthy",
            "total_engines": 0,
            "running_engines": 0
        },
        "logs": {
            "status": "healthy",
            "path_exists": true
        }
    }
}
```

---

## Success Criteria

All 12 tests must pass for the application to be considered production-ready.

**Test Results Summary**:
- Tests Passed: ___/12
- Tests Failed: ___/12
- Blockers: ___
