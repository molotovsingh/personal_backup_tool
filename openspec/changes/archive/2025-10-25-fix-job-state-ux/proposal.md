# Proposal: Fix Job State UX Issues

## Why
Current Jobs page UX creates confusion and violates user expectations around job state management. The crash recovery prompt has misleading button labels ("Resume" doesn't actually resume jobs, "Ignore" modifies job state), completed jobs show disabled buttons that suggest blocked functionality, and users lack a manual refresh option when all jobs are idle.

## What Changes
- **Crash recovery clarity**: Rename "Resume Interrupted Jobs" → "Recover (mark as paused)" with help text; change "Ignore" → "Dismiss" that truly dismisses without modifying job statuses
- **Completed job display**: Remove disabled Start button from completed jobs; show status badge "✓ Completed" instead
- **Manual refresh**: Add "🔄 Refresh" button on Jobs page when no jobs are running (auto-refresh is inactive)

## Impact
- **Affected specs**: crash-recovery-clarity (new), completed-job-display (new), manual-refresh (new)
- **Affected code**: `app.py` only (lines 108-133 for recovery, 875-898 for buttons, 374-383 for refresh)
- **No breaking changes**: All changes are UI/UX improvements with no API, data model, or configuration changes
- **Testing**: Manual UI testing required for all three scenarios
- **Rollback**: Simple git revert if issues arise
