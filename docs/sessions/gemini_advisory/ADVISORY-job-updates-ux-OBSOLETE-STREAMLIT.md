# ⚠️ OBSOLETE - UX Advisory — Job Updates and Recovery (Streamlit App)

**Status:** OBSOLETE - Streamlit app has been retired
**Date Archived:** 2025-10-26
**Reason:** This advisory referenced the legacy Streamlit app (`app.py`) which has been fully retired and replaced by the Flask app. The UX issues documented here were addressed during the Flask migration.

**Replacement:** See `FLASK_MIGRATION_COMPLETE.md` and `FLASK_UX_HARDENING_COMPLETE.md` for how these issues were resolved in Flask.

---

## Original Advisory (For Historical Reference)

Summary

- Several small UX inconsistencies around job state updates and crash recovery can mislead users or cause unintended actions.
- This advisory documents the issues, impact, and proposes low‑risk, targeted fixes with references to current code locations in the **legacy Streamlit app**.

Key Issues

1) Crash recovery prompt actions are misleading and unsafe
- Problem: The sidebar prompt shows “Resume Interrupted Jobs”, but the action marks jobs as paused. The “Ignore” button also marks all interrupted jobs as paused (same side effect), which violates user expectations for “Ignore”.
- Impact: Users may click Ignore expecting no changes; instead statuses change to paused. “Resume” wording suggests actual resume, but no jobs are started.
- Evidence:
  - `app.py:108` — “Resume Interrupted Jobs” button marks each interrupted job paused.
  - `app.py:123` — “Ignore” button also marks each interrupted job paused.
- Recommendation (low-risk):
  - Rename “Resume Interrupted Jobs” → “Recover Interrupted Jobs (mark as paused)”.
  - Make “Ignore” a true dismiss: do not modify any job statuses; only hide the prompt.
  - Optional: Add a follow‑up CTA “Start All Paused Jobs” to actually resume.

2) Disabled “Start” button for completed jobs is confusing
- Problem: Completed jobs render a disabled “▶️ Start” button.
- Impact: Suggests an action exists but is blocked; increases confusion and clutter.
- Evidence:
  - `app.py:884` — Renders a disabled Start button when status not in startable states (includes completed).
- Recommendation (low-risk):
  - Do not render a disabled Start for completed jobs. Instead show a neutral status chip (e.g., “✓ Completed”) and keep “🗑️ Delete” and “📄 View Logs”.
  - Optional: add a “Run Again” flow (new job prefilled) as a separate enhancement.

3) No manual refresh on Jobs page when no jobs are running
- Problem: Auto‑refresh only runs when at least one job is running. When all jobs are idle, the UI can feel stale, and users must navigate away/back to refresh.
- Impact: Minor friction; users performing checks after a job finishes get no quick refresh affordance.
- Evidence:
  - `app.py:372` — `st_autorefresh` is gated by “has running jobs”.
- Recommendation (low-risk):
  - Add a compact “🔄 Refresh” button near the Jobs header to trigger `st.rerun()` when auto‑refresh is inactive.

Copy and UI Suggestions

- Recovery prompt
  - Header: “Interrupted jobs detected” (unchanged)
  - Primary action: “Recover (mark as paused)” — help: “Ensures safe state; you can resume manually.”
  - Secondary action: “Dismiss” — help: “Hide this message. No changes to job statuses.”

- Completed job card
  - Replace disabled Start with: Caption “✓ Completed” and a small “📄 View Logs” button.

Testing Plan

1) Crash recovery
- Preconditions: Set a job’s status to `running` in storage and load the app.
- Expect: Sidebar shows recovery prompt.
- Actions: Click “Recover (mark as paused)” — expect statuses set to paused; message confirms change.
- Actions: Recreate scenario; click “Dismiss” — expect no status changes.

2) Completed job card
- Preconditions: A job with `status=completed`.
- Expect: No disabled Start button; completed chip visible; Delete and View Logs present.

3) Manual refresh
- Preconditions: No running jobs.
- Expect: Jobs page shows a “🔄 Refresh” control; clicking re-renders state.

Notes

- This advisory focuses on UX and copy. No engine/runtime logic changes required.
- All recommended changes are localized to `app.py` and are low risk, reversible, and testable via manual UI checks.

File References

- Recovery actions: `app.py:108`, `app.py:123`
- Disabled Start rendering: `app.py:884`
- Jobs auto‑refresh gating: `app.py:372`

