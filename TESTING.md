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

2. Run the app: `uv run python flask_app.py`

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

3. Restart the app: `uv run python flask_app.py`

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

## Success Criteria

All 11 tests must pass for the application to be considered production-ready.

**Test Results Summary**:
- Tests Passed: ___/11
- Tests Failed: ___/11
- Blockers: ___
