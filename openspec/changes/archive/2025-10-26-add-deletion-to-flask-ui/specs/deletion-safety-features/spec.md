# Spec: Deletion Safety Features

## Summary
Display deletion progress, status indicators, and safety information in the Flask UI to keep users informed during deletion operations.

## ADDED Requirements

### Requirement: Deletion progress display in job detail view
The system SHALL display the current deletion phase and metrics when a job with deletion enabled is running.

#### Scenario: Job shows deletion verification phase
```python
# Given: Job with verify_then_delete mode is running
job = manager.get_job('deletion_job_id')
# And: Transfer completed, verification in progress
job['progress']['deletion']['phase'] = 'verifying'

# When: User views job detail page
# Then: UI displays verification status
# Expected UI element:
# <div class="deletion-phase">
#   Phase: Verifying backup integrity
# </div>
```

#### Scenario: Job shows active deletion phase with progress
```python
# Given: Job is deleting files
job = manager.get_job('deletion_job_id')
job['progress']['deletion']['phase'] = 'deleting'
job['progress']['deletion']['files_deleted'] = 150
job['progress']['deletion']['bytes_deleted'] = 524288000  # ~500MB

# When: User views job detail page
# Then: UI displays deletion progress
# Expected UI:
# "Deleting files: 150 files deleted (500.0 MB)"
```

#### Scenario: Job shows completed deletion
```python
# Given: Job completed with deletion
job = manager.get_job('deletion_job_id')
job['progress']['deletion']['phase'] = 'completed'
job['progress']['deletion']['files_deleted'] = 7303
job['progress']['deletion']['bytes_deleted'] = 607632103

# When: User views job detail page
# Then: UI shows completion summary
# Expected UI:
# "✅ Deletion completed: 7,303 files deleted (579.5 MB)"
```

### Requirement: Visual warnings for deletion-enabled jobs
The system SHALL display prominent visual indicators for jobs with deletion enabled throughout the UI to prevent accidental triggers.

#### Scenario: Job list shows deletion badge
```python
# Given: Job list contains job with deletion enabled
job = {
    'id': 'abc123',
    'name': 'risky_backup',
    'settings': {'delete_source_after': True, 'deletion_mode': 'verify_then_delete'}
}

# When: Dashboard renders job list
# Then: Job shows deletion warning badge
# Expected UI element:
# <span class="badge badge-danger">
#   🗑️ Deletion Enabled
# </span>
```

#### Scenario: Job detail shows deletion mode badge
```python
# Given: User viewing job with per-file deletion
job = {
    'settings': {'delete_source_after': True, 'deletion_mode': 'per_file'}
}

# When: Job detail page renders
# Then: Deletion mode is prominently displayed
# Expected UI:
# <div class="alert alert-warning">
#   ⚡ Per-File Deletion Mode Active
# </div>
```

### Requirement: Safety features information display
The system SHALL display active safety mechanisms when deletion is enabled.

#### Scenario: Form shows enabled safety features
```html
<!-- Given: User has enabled deletion on job form -->
<!-- When: Form renders deletion settings -->
<!-- Then: Safety features are listed -->

<div class="alert alert-success">
  🛡️ **Safety features enabled:**
  - Pre-deletion space verification (10% margin)
  - Complete audit log of all deletions
  - Deletion count tracking
  - Option to skip deletion on each run
</div>
```

#### Scenario: Job detail shows deletion audit trail
```python
# Given: Job completed deletion
job_id = 'completed_deletion_job'

# When: User views job logs page filtered for this job
# Then: Deletion log entries are visible
# Expected log format:
# [2025-10-26 10:15:23] ⚠️ DELETION MODE ENABLED: verify_then_delete
# [2025-10-26 10:20:45] Starting backup verification with checksums...
# [2025-10-26 10:25:12] ✅ Verification passed - proceeding with deletion
# [2025-10-26 10:25:13] Deleting 7303 file(s) from source...
# [2025-10-26 10:27:58] ✅ Deletion completed successfully
```
