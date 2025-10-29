# Rclone Workflow Hardening Proposal

**Date:** 2025-10-26
**Change ID:** `harden-rclone-workflow`
**Status:** ✅ Validated, Ready for Review
**Source:** Gemini Advisory - `ADVISORY-rclone-workflow-hardening.md`

---

## Summary

This proposal addresses 5 correctness and operability issues in the rclone engine identified through code audit, converting the advisory into an actionable OpenSpec change proposal.

## Issues Addressed

### 1. Per-File Deletion Retry Bug (CRITICAL - Correctness)
- **Problem:** Retry after network error uses `rclone copy` instead of `rclone move`
- **Impact:** Per-file deletion semantics broken, sources accumulate files
- **Fix:** Check deletion mode in `_restart_process()` and use correct operation

### 2. Verify-After Mode Ignored
- **Problem:** `verification_mode='verify_after'` only works when deletion enabled
- **Impact:** Users can't verify backups without enabling deletion
- **Fix:** Run verification after transfer regardless of deletion setting

### 3. Missing Rclone Binary Preflight Check
- **Problem:** Jobs fail with generic errors when rclone not installed
- **Impact:** Poor UX, confusing error messages
- **Fix:** Check `is_rclone_installed()` before job creation

### 4. Remote Cleanup Incomplete
- **Problem:** `rclone delete` leaves empty directory trees on remotes
- **Impact:** Cloud storage accumulates empty directories
- **Fix:** Run `rclone rmdirs` after successful delete

### 5. Logs Path Mismatch
- **Problem:** Engines write to `~/backup-manager/logs`, Flask reads from `logs/`
- **Impact:** Rclone/rsync logs invisible in Flask UI
- **Fix:** Unify paths via `BACKUP_MANAGER_DATA_DIR` env var

## OpenSpec Artifacts Created

### Proposal Documents
- **`proposal.md`** - Problem statement, solutions, alternatives, risks
- **`tasks.md`** - 18 implementation tasks organized in 4 phases

### Spec Deltas (5 Capabilities)

1. **`rclone-retry-correctness`** (MODIFIED)
   - 3 scenarios covering per-file, verify-then-delete, and no-deletion retries
   - Ensures operation type preserved across retries

2. **`rclone-verification-mode`** (MODIFIED)
   - 5 scenarios for verify-after independent of deletion
   - Progress tracking during verification

3. **`rclone-preflight-checks`** (ADDED - New Spec)
   - 3 scenarios for binary validation
   - Clear error messages when rclone missing

4. **`rclone-remote-cleanup`** (ADDED - New Spec)
   - 3 scenarios for empty directory cleanup
   - Graceful handling of rmdirs failures

5. **`data-directory-unification`** (ADDED - New Spec)
   - 6 scenarios for unified data paths
   - Environment variable configuration
   - Auto-creation of directory structure

## Implementation Phasing

### Phase 1: Quick Wins (Low Risk, 25 min)
- Add rclone preflight check
- Fix per-file deletion retry operation

### Phase 2: Verification (30 min)
- Implement verify-after mode
- Add verification progress tracking

### Phase 3: Remote Cleanup (15 min)
- Add rmdirs after remote delete

### Phase 4: Data Unification (35 min, Moderate Risk)
- Define BACKUP_MANAGER_DATA_DIR
- Update rclone/rsync engines
- Update storage paths

**Total Estimated Effort:** ~105 minutes (~2 hours)

## Risk Assessment

### Low Risk (4 changes)
- Per-file retry: Single conditional, minimal code change
- Verify-after: Optional feature, no impact when disabled
- Preflight: Early failure, no state changes
- Remote rmdirs: Runs after success, errors logged but not fatal

### Moderate Risk (1 change)
- Data unification: Multi-file coordination required
  - **Mitigation:** Defaults to current behavior
  - **Testing:** Verify with both default and custom paths

## Testing Requirements

5 core tests required:
1. Per-file retry with simulated network error
2. Verify-after with deletion disabled
3. Preflight check with missing rclone
4. Remote deletion + rmdirs invocation
5. Integration: logs visible in Flask UI

## Files to Modify

### Core Changes
- `engines/rclone_engine.py` - Retry logic, verification, rmdirs, log paths
- `core/job_manager.py` - Preflight check
- `flask_app/config.py` - Unified data directory

### Supporting Changes
- `engines/rsync_engine.py` - Log path unification
- `core/storage/*.py` - Storage path unification

### No Changes Required
- `utils/rclone_helper.py` - Already has `is_rclone_installed()`
- Verification logic - `_verify_backup()` already exists

## Success Criteria

All 5 issues resolved:
- ✅ Per-file retry uses move (not copy)
- ✅ Verify-after works independently
- ✅ Clear "rclone not found" errors
- ✅ Remote directories cleaned up
- ✅ Logs appear in Flask UI

## Next Steps

1. Review this proposal
2. Approve for implementation or provide feedback
3. Implement in phases (can be done incrementally)
4. Test each phase before proceeding
5. Archive proposal when complete

## Validation Status

✅ **Proposal validated with `openspec validate --strict`**
- All 5 spec deltas well-formed
- Requirements have scenario coverage
- Tasks are ordered and verifiable
- No blocking issues found

---

**Advisory Source:** `gemini_advisory/ADVISORY-rclone-workflow-hardening.md`
**Proposal Location:** `openspec/changes/harden-rclone-workflow/`
