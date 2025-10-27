# Tasks

## Implementation Tasks

### Phase 1: Quick Wins (Low Risk, High Value)

- [ ] Add rclone preflight check in JobManager
  - **File:** `core/job_manager.py:147`
  - **Change:** Before `RcloneEngine(...)`, call `is_rclone_installed()` and return error if False
  - **Validation:** Rename rclone binary temporarily, attempt to start job, verify clear error message
  - **Dependencies:** None
  - **Estimated effort:** 10 minutes

- [ ] Fix per-file deletion retry operation
  - **File:** `engines/rclone_engine.py:332`
  - **Change:** In `_restart_process()`, check `self.delete_source_after and self.deletion_mode == 'per_file'` and set `operation = 'move'`
  - **Additional:** Add `--delete-empty-src-dirs` flag when operation is move
  - **Validation:** Create test with network error simulation, verify retry uses move
  - **Dependencies:** None
  - **Estimated effort:** 15 minutes

### Phase 2: Verification Enhancement

- [ ] Implement verify-after mode
  - **File:** `engines/rclone_engine.py` (after transfer completion logic)
  - **Change:** After successful transfer, if `self.verification_mode == 'verify_after'`, call `self._verify_backup()`
  - **Update:** Set `progress['verification']['passed']`, `progress['verification']['files_checked']`
  - **Validation:** Test job with verify-after and deletion disabled, confirm verification runs
  - **Dependencies:** None
  - **Estimated effort:** 20 minutes

- [ ] Add verification progress tracking
  - **File:** `engines/rclone_engine.py:_verify_backup()`
  - **Change:** Update `self.progress['verification']` fields during verification
  - **Validation:** Monitor progress dict during verification, confirm fields populate
  - **Dependencies:** Verify-after mode implemented
  - **Estimated effort:** 10 minutes

### Phase 3: Remote Cleanup

- [ ] Add rmdirs after remote delete
  - **File:** `engines/rclone_engine.py:520-530` (in `_delete_verified_files()`)
  - **Change:** After `rclone delete` succeeds, invoke `subprocess.run(['rclone', 'rmdirs', self.source])`
  - **Logging:** Log "Removing empty directories from remote..." and handle errors
  - **Validation:** Use test remote or mock, verify rmdirs is called
  - **Dependencies:** None
  - **Estimated effort:** 15 minutes

### Phase 4: Data Path Unification (Moderate Risk)

- [ ] Define BACKUP_MANAGER_DATA_DIR environment variable
  - **File:** `flask_app/config.py:15-30`
  - **Change:** Add `BACKUP_MANAGER_DATA_DIR = os.getenv('BACKUP_MANAGER_DATA_DIR', str(Path.home() / 'backup-manager'))`
  - **Derive:** `LOGS_DIR = Path(BACKUP_MANAGER_DATA_DIR) / 'logs'`
  - **Validation:** Check config loads with default and custom env values
  - **Dependencies:** None
  - **Estimated effort:** 10 minutes

- [ ] Update rclone engine to use unified data dir
  - **File:** `engines/rclone_engine.py:66`
  - **Change:** Import BACKUP_MANAGER_DATA_DIR or read from env, set `self.log_file = Path(data_dir) / 'logs' / f'rclone_{job_id}.log'`
  - **Validation:** Verify log files created in correct location
  - **Dependencies:** Data dir env var defined
  - **Estimated effort:** 10 minutes

- [ ] Update rsync engine to use unified data dir
  - **File:** `engines/rsync_engine.py` (similar line to rclone)
  - **Change:** Use unified data dir for log path
  - **Validation:** Verify rsync logs in correct location
  - **Dependencies:** Data dir env var defined
  - **Estimated effort:** 5 minutes

- [ ] Update storage to use unified data dir
  - **File:** `core/storage/json_storage.py` or similar
  - **Change:** Use unified data dir for jobs/settings storage
  - **Validation:** Verify storage reads/writes from correct location
  - **Dependencies:** Data dir env var defined
  - **Estimated effort:** 10 minutes

## Testing Tasks

- [ ] Test per-file retry with network error
  - **Approach:** Inject network error during per-file move, monitor `_restart_process()` call
  - **Assert:** Command uses 'move' not 'copy', `--delete-empty-src-dirs` present
  - **Dependencies:** Per-file retry fix implemented

- [ ] Test verify-after mode independently
  - **Approach:** Create job with `verification_mode='verify_after'`, `delete_source_after=False`
  - **Assert:** Verification runs, `progress['verification']['passed']` is True or False
  - **Dependencies:** Verify-after mode implemented

- [ ] Test preflight check with missing rclone
  - **Approach:** Temporarily mask rclone from PATH
  - **Assert:** Job creation fails with "rclone not found" error
  - **Dependencies:** Preflight check implemented

- [ ] Test remote rmdirs invocation
  - **Approach:** Mock or use test remote, enable deletion
  - **Assert:** `rclone rmdirs` is invoked after `rclone delete`
  - **Dependencies:** Remote rmdirs implemented

- [ ] Integration test: Verify logs appear in UI
  - **Approach:** Run rclone job, navigate to Flask logs page
  - **Assert:** Rclone log entries visible in filter/export
  - **Dependencies:** Data path unification complete

## Documentation Tasks

- [ ] Document BACKUP_MANAGER_DATA_DIR environment variable
  - **File:** `README.md` or configuration docs
  - **Content:** Explain env var, default value, when to override
  - **Dependencies:** Data path unification complete

- [ ] Update deployment/installation docs if needed
  - **Content:** Note about logs location, data directory structure
  - **Dependencies:** All implementation complete

## Optional Future Work (Not in Scope)

- [ ] Expand network error pattern list
- [ ] Add `--fast-list` option for large remote deletions
- [ ] Document performance implications of `--checksum` mode
- [ ] Add configurable stderr window for error detection
