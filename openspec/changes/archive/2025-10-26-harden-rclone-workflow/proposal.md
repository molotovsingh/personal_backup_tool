# Proposal: Harden Rclone Workflow

## Why

The rclone engine is robust for transfers, progress tracking, and network retries, but has several correctness and operability gaps identified through audit:

1. **Per-file deletion retry bug**: When network errors cause retry with `deletion_mode='per_file'`, the restart uses `rclone copy` instead of `rclone move`, breaking per-file deletion semantics
2. **Verify-after mode ignored**: Setting `verification_mode='verify_after'` has no effect unless deletion is also enabled
3. **No rclone binary preflight check**: Jobs fail with generic errors instead of clear "rclone not installed" messages
4. **Remote cleanup incomplete**: Deleting files from remotes leaves empty directory trees
5. **Logs path mismatch**: Engines write logs to `~/backup-manager/logs` but Flask UI reads from `logs/` (repo), causing logs to not appear in UI

These issues affect correctness (per-file mode), user experience (missing verification, unclear errors, invisible logs), and remote storage cleanliness.

## What Changes

### 1. Fix Per-File Deletion Retry (Correctness Bug)
**File:** `engines/rclone_engine.py:332`

- In `_restart_process()`, check deletion settings and use `operation = 'move'` when `delete_source_after` and `deletion_mode == 'per_file'`
- Add `--delete-empty-src-dirs` flag for move operations (matching `start()` behavior)
- **Impact:** Ensures retry attempts continue using move semantics, preventing source accumulation

### 2. Honor Verify-After Mode
**File:** `engines/rclone_engine.py:455`

- After successful transfer completion, check if `verification_mode == 'verify_after'`
- Call `_verify_backup()` even when deletion is disabled
- Update `progress['verification']` fields (passed, files_checked, mismatches)
- **Impact:** Users get verification when requested, regardless of deletion settings

### 3. Add Rclone Binary Preflight Check
**Files:** `core/job_manager.py:147`, `utils/rclone_helper.py:12`

- Before creating `RcloneEngine`, call `is_rclone_installed()` helper
- If not installed, return clear error message to UI: "rclone not found - install from rclone.org"
- **Impact:** Better error messages, faster failure detection

### 4. Clean Empty Directories on Remote Deletion
**File:** `engines/rclone_engine.py:520-611`

- After successful `rclone delete` on remote sources, invoke `rclone rmdirs <source>`
- Log the outcome and handle non-zero return codes gracefully
- **Impact:** Prevents accumulation of empty directory trees on cloud remotes

### 5. Unify Data Directory Paths
**Files:** `flask_app/config.py:28`, `engines/rclone_engine.py:66`, `engines/rsync_engine.py`

- Introduce `BACKUP_MANAGER_DATA_DIR` environment variable
- Default to `~/backup-manager` (current behavior)
- Derive logs, jobs, settings paths from this single root
- Update both engines and Flask config to use unified paths
- **Impact:** Logs appear in Flask UI, easier deployment configuration

## Alternatives Considered

### Per-File Retry Fix
- **Alternative:** Rewrite entire retry logic - **Rejected:** Overly complex, existing logic works except for this one check
- **Chosen:** Minimal fix - add deletion mode check in `_restart_process()`

### Verify-After Implementation
- **Alternative:** Add new post-transfer hook system - **Rejected:** Over-engineering for single feature
- **Chosen:** Direct check after transfer success, reuse existing `_verify_backup()` function

### Logs Path Unification
- **Alternative:** Symlink `~/backup-manager/logs` to `logs/` - **Rejected:** Platform-specific, fragile
- **Alternative:** Make Flask read from `~/backup-manager` - **Rejected:** Only solves one side
- **Chosen:** Single env-configurable data root used by all components

## Dependencies

- No new external dependencies
- Existing helpers: `is_rclone_installed()` already available in `utils/rclone_helper.py`
- Existing verification: `_verify_backup()` already implemented

## Success Criteria

### Functional
- [ ] Per-file retry uses `rclone move` after network errors (not `copy`)
- [ ] Verify-after mode runs verification even when deletion is disabled
- [ ] Jobs fail fast with clear error when rclone is missing
- [ ] Remote deletions remove empty directories
- [ ] Rclone logs appear in Flask UI logs page

### Testing
- [ ] Simulate network error during per-file move, verify retry uses move
- [ ] Test verify-after with deletion disabled, confirm verification runs
- [ ] Test with rclone unavailable, verify clear error message
- [ ] Test remote deletion, verify rmdirs is invoked
- [ ] Run job and confirm logs appear in UI

## Risk Assessment

**Low Risk Changes:**
- Per-file retry fix: One conditional check, low blast radius
- Verify-after: Optional behavior, performance impact only when enabled
- Preflight check: Fails early with clear message, no state changes
- Remote rmdirs: Runs after deletion succeeds, safe operation

**Moderate Risk Change:**
- Data path unification: Requires coordination between multiple files
  - **Mitigation:** Default to current behavior (`~/backup-manager`)
  - **Rollout:** Document env var, test with both default and custom paths
  - **Validation:** Verify logs/jobs/settings all use same root

## Additional Improvements (Nice-to-Have)

These are NOT included in this proposal but could be future work:

- Expand network error pattern list (`dial tcp`, `connection reset by peer`)
- Consider `--fast-list` for `rclone delete` on very large directory trees
- Document performance trade-offs of `--checksum` mode
- Add configurable stderr window size for error pattern matching
