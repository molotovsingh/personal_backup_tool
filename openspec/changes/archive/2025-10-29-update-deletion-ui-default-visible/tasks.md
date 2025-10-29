## 1. Implementation
- [x] 1.1 jobs.html: Default `delete_source_after` to checked
- [x] 1.2 jobs.html: Render deletion options on initial load (server render OR HTMX `load` trigger)
- [x] 1.3 jobs.html: Remove `hx-on::before-request` alert gating
- [x] 1.4 Ensure server validation still blocks creation if `deletion_confirmed` is false
- [x] 1.5 Tests: Update for default-visible behavior and no-alert rule

## 2. Validation
- [x] 2.1 Manual: Open form → deletion options visible, no flicker
- [x] 2.2 Manual: Uncheck → options disappear; recheck → options return
- [x] 2.3 Manual: Submit with deletion=ON, confirmation=OFF → inline/server error; no alert
- [x] 2.4 Automated: Update tests to assert initial GET for `/jobs/deletion-ui?delete_source_after=true` (if HTMX) and server refusal without confirmation

## 3. Docs
- [x] 3.1 Update user guide screenshots (optional)

