# Tasks: Fix Job State UX Issues

## Implementation Order

These tasks are ordered to deliver incremental user-visible improvements. Each task is independently verifiable through manual UI testing.

### 1. Fix crash recovery prompt actions
**Capability**: crash-recovery-clarity
**Location**: `app.py:108-133`
**Changes**:
- Rename "Resume Interrupted Jobs" button to "Recover (mark as paused)"
- Add help text: "Ensures safe state; you can resume manually."
- Change "Ignore" button to "Dismiss"
- Remove job status modification from Dismiss action (lines 124-130)
- Update success message to be clearer about what happened
- Keep the same recovery detection logic (app.py:102-106)

**Verification**:
- Start app with a job set to status=running in jobs.yaml
- Verify sidebar shows recovery prompt with new button labels
- Click "Recover (mark as paused)" → jobs marked as paused, message confirms
- Reset scenario, click "Dismiss" → jobs unchanged, prompt hidden
- Verify help text appears on hover

**Dependencies**: None
**Parallelizable**: Yes (independent from other tasks)

---

### 2. Remove disabled Start button for completed jobs
**Capability**: completed-job-display
**Location**: `app.py:875-898`
**Changes**:
- Modify button rendering logic to check for `status == 'completed'`
- For completed jobs: render status badge "✓ Completed" instead of disabled button
- Keep Delete and View Logs actions visible
- For running jobs: continue showing Pause button (no Start button)
- For startable jobs (pending/paused/failed): continue showing enabled Start button

**Verification**:
- Create job and let it complete (or manually set status=completed)
- View Jobs page → no disabled Start button, see "✓ Completed" badge
- Verify Delete and View Logs still available
- Test pending job → enabled Start button shows
- Test running job → Pause button shows, no Start button

**Dependencies**: None
**Parallelizable**: Yes (independent from other tasks)

---

### 3. Add manual refresh button for Jobs page
**Capability**: manual-refresh
**Location**: `app.py:374-383` (near title section)
**Changes**:
- After title, check if `has_running_jobs_on_jobs_page` is False
- If False, render compact "🔄 Refresh" button (not full-width)
- Button callback: `st.rerun()`
- Position near header using columns layout
- Keep existing LIVE indicator logic for when jobs are running

**Verification**:
- Jobs page with all jobs idle → "🔄 Refresh" button visible, no LIVE indicator
- Click refresh → page reloads, states updated
- Start a job → refresh button disappears, LIVE indicator shows
- Stop job → refresh button reappears

**Dependencies**: None
**Parallelizable**: Yes (independent from other tasks)

---

## Testing Checklist

After implementing all tasks, verify the complete flow:

- [x] Crash recovery: "Recover" marks as paused, "Dismiss" changes nothing
- [x] Completed job card: no disabled buttons, only status badge and relevant actions
- [x] Manual refresh: appears when idle, hidden when running, triggers re-render
- [x] No regressions: existing job start/pause/delete flows still work
- [x] Visual consistency: new UI elements match existing styling
- [x] Help text: hover states work correctly

## Rollback Plan

If issues arise:
1. All changes are in `app.py` only
2. Revert to previous version using git
3. No data migrations or storage changes needed
4. No configuration changes required

## Future Enhancements (Not in Scope)

- "Run Again" functionality for completed jobs (new job prefilled)
- Batch operations on multiple jobs
- Keyboard shortcuts for common actions
