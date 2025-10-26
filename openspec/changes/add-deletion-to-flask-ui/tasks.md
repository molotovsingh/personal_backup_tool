# Tasks: Add Source Deletion Feature to Flask UI

## Phase 1: Job Creation Form - Deletion Controls

- [ ] **Add deletion checkbox to job creation form**
  - Update `flask_app/templates/jobs.html` create job form
  - Add checkbox: "Delete source files after successful backup"
  - Default to unchecked
  - **Validation**: Checkbox appears in form, unchecked by default

- [ ] **Add deletion mode radio buttons**
  - Show radio buttons when deletion checkbox is checked
  - Options: "Verify Then Delete (Safest)" and "Per-File Deletion (Faster)"
  - Default to "verify_then_delete"
  - Use HTMX to show/hide based on checkbox state
  - **Validation**: Radio buttons appear/hide correctly on checkbox toggle

- [ ] **Add mode-specific explanations**
  - Create info boxes explaining each deletion mode
  - Verify-then-delete: Show 4-step process (transfer → verify → delete → audit)
  - Per-file: Show warning about lack of verification
  - Style with appropriate colors (info blue for verify, warning orange for per-file)
  - **Validation**: Correct explanation shows based on selected mode

- [ ] **Add safety features information box**
  - Display list of enabled safety features
  - Include: space verification, audit logging, count tracking, skip option
  - Style as success/green alert box
  - **Validation**: Safety info box visible when deletion enabled

- [ ] **Add confirmation checkbox**
  - Text: "I understand that source files will be PERMANENTLY DELETED"
  - Required when deletion enabled
  - Show error message if deletion enabled but not confirmed
  - **Validation**: Form submission blocked without confirmation

- [ ] **Add deletion warning banner**
  - Prominent red/danger alert when deletion checkbox checked
  - Text: "WARNING: Source files will be permanently deleted after backup!"
  - **Validation**: Warning appears immediately on checkbox toggle

## Phase 2: Backend Integration

- [ ] **Update job creation route to handle deletion settings**
  - Modify `flask_app/routes/jobs.py` create_job route
  - Extract deletion form fields: `delete_source_after`, `deletion_mode`, `deletion_confirmed`
  - Pass to service layer
  - **Validation**: Form data correctly extracted from POST request

- [ ] **Update job service validation**
  - Modify `services/job_service.py` `create_job_from_form()`
  - Validate deletion settings:
    - If `delete_source_after=True`, require `deletion_confirmed=True`
    - Validate `deletion_mode` is one of: 'verify_then_delete', 'per_file'
  - Return appropriate error messages
  - **Validation**: Invalid deletion settings rejected with clear errors

- [ ] **Pass deletion settings to JobManager**
  - Update `job_service.py` to include deletion settings in job creation
  - Ensure settings dict includes all deletion fields
  - **Validation**: Job created in jobs.yaml includes deletion settings

## Phase 3: Job Display - Status Indicators

- [ ] **Add deletion badge to job list**
  - Update `flask_app/templates/partials/jobs_list.html`
  - Show "🗑️ Deletion Enabled" badge for jobs with `delete_source_after=True`
  - Style as danger/red badge
  - **Validation**: Badge appears on jobs with deletion, not on others

- [ ] **Add deletion mode indicator to job detail**
  - Update job detail partial template
  - Show deletion mode badge when deletion enabled
  - Different styles for verify_then_delete vs per_file
  - **Validation**: Correct mode displayed in job detail view

- [ ] **Display deletion progress in running jobs**
  - Update job detail template to show `progress.deletion` data
  - Display current phase: transfer, verifying, deleting, completed
  - Show metrics: files_deleted, bytes_deleted
  - Format bytes as human-readable (MB, GB)
  - **Validation**: Deletion progress updates in real-time during job execution

## Phase 4: Job Detail - Deletion Metrics

- [ ] **Show deletion phase status**
  - Create UI element for deletion phase indicator
  - Map phases to user-friendly text:
    - 'transfer' → "Transferring files..."
    - 'verifying' → "Verifying backup integrity..."
    - 'deleting' → "Deleting source files..."
    - 'completed' → "✅ Deletion completed"
    - 'failed' → "❌ Deletion failed"
  - **Validation**: Phase indicator updates as job progresses

- [ ] **Display deletion statistics**
  - Show files deleted count with formatting (e.g., "7,303 files")
  - Show bytes deleted with human-readable units
  - Calculate and show deletion progress percentage during delete phase
  - **Validation**: Stats display correctly for completed deletion jobs

- [ ] **Show deletion logs**
  - Ensure logs page filters show deletion-related log entries
  - Highlight deletion events (⚠️, ✅, ❌ icons)
  - **Validation**: Deletion logs visible in logs page for deletion jobs

## Phase 5: Testing & Documentation

- [ ] **Manual testing - job creation**
  - Test creating job with deletion enabled
  - Test both deletion modes
  - Test confirmation requirement
  - Test form validation errors
  - **Validation**: All form controls work as expected

- [ ] **Manual testing - job execution**
  - Run job with verify_then_delete mode
  - Verify progress indicators update correctly
  - Check deletion actually occurs (verify source files deleted)
  - Check logs contain deletion entries
  - **Validation**: End-to-end deletion workflow functional

- [ ] **Manual testing - per-file mode**
  - Run job with per_file deletion mode
  - Verify files deleted during transfer (not after)
  - Check empty directories cleaned up
  - **Validation**: Per-file deletion works correctly

- [ ] **Manual testing - deletion failure scenarios**
  - Test verification failure (modify dest file, re-run with verify_then_delete)
  - Verify source files NOT deleted when verification fails
  - Check error messages displayed
  - **Validation**: Safety mechanisms prevent deletion on verification failure

- [ ] **Update user documentation**
  - Document deletion feature in README or user guide
  - Explain both modes and when to use each
  - Document safety features
  - Add screenshots of UI
  - **Deliverable**: Documentation update committed

- [ ] **Feature parity checklist**
  - Compare Flask UI with Streamlit UI deletion feature
  - Verify all Streamlit deletion functionality present in Flask
  - Document any intentional differences
  - **Validation**: Flask UI matches Streamlit UI for deletion features

## Dependencies
- **Phase 1** (UI controls) must complete before Phase 2 (backend integration)
- **Phase 2** must complete before Phase 3-4 (display features need working backend)
- **Phase 5** (testing) depends on all previous phases

## Parallelizable Work
- UI templates (Phase 1, 3, 4) can be developed in parallel with different developers
- Documentation (Phase 5) can be drafted while implementation progresses
- Manual test plans can be written before implementation completes
