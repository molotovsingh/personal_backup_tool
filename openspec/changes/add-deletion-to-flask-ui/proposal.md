# Proposal: Add Source Deletion Feature to Flask UI

## Why
The backend engines (rsync/rclone) and Streamlit UI already support source file deletion after successful backup with verification, but this critical feature was not migrated to the Flask UI during the Streamlit→Flask migration. Users who rely on the deletion feature for backup-and-cleanup workflows cannot use the Flask app, creating feature parity issues between the two frontends.

## What Changes
- **Add deletion controls to job creation form**: Checkbox to enable deletion, radio buttons for mode selection ('verify_then_delete' vs 'per_file'), confirmation checkbox for safety
- **Display deletion warnings and safety info**: Show clear warnings about permanent deletion, explain each mode, display enabled safety features
- **Pass deletion settings to backend**: Update job service to accept and validate deletion parameters
- **Show deletion progress in job detail**: Display deletion phase (verifying, deleting, completed), files deleted count, bytes deleted
- **Deletion status indicators**: Show visual indicators when job has deletion enabled (warning badges, special colors)

## Impact
- **Affected specs**: 2 capabilities (deletion-ui-controls, deletion-safety-features)
- **Affected code**:
  - `flask_app/templates/jobs.html`: Add deletion form controls
  - `flask_app/templates/partials/job_detail.html`: Show deletion progress
  - `flask_app/routes/jobs.py`: Handle deletion form data
  - `services/job_service.py`: Validate deletion settings, pass to JobManager
- **Feature parity**: Achieves full parity with Streamlit UI for deletion functionality
- **No backend changes**: Backend already supports deletion, only UI needs updates
- **No breaking changes**: Existing jobs without deletion continue working normally
- **Safety**: Requires explicit user confirmation before enabling deletion
