# Spec: Deletion UI Controls

## Summary
Add user interface controls to the Flask job creation form for configuring source file deletion after successful backup.

## ADDED Requirements

### Requirement: Deletion mode selection in job creation form
The system SHALL provide users the ability to enable source deletion and choose between 'verify_then_delete' and 'per_file' modes when creating a backup job.

#### Scenario: User enables deletion with verify-then-delete mode
```python
# Given: User is creating a new backup job
# When: User fills job creation form with:
#   - Job name: "critical_backup"
#   - Source: "/data/important"
#   - Dest: "/backup/important"
#   - Delete source after backup: checked
#   - Deletion mode: "Verify Then Delete (Safest)"
#   - Confirmation: "I understand files will be permanently deleted": checked

# Then: Job is created with deletion settings
job = manager.get_job('critical_backup')
assert job['settings']['delete_source_after'] == True
assert job['settings']['deletion_mode'] == 'verify_then_delete'
assert job['settings']['deletion_confirmed'] == True
```

#### Scenario: User enables deletion with per-file mode
```python
# Given: User is creating a new backup job
# When: User fills job creation form with:
#   - Delete source after backup: checked
#   - Deletion mode: "Per-File Deletion (Faster)"
#   - Confirmation: checked

# Then: Job is created with per-file deletion mode
job = manager.get_job('test_job')
assert job['settings']['deletion_mode'] == 'per_file'
```

### Requirement: Explicit confirmation required before enabling deletion
The system SHALL require users to explicitly confirm understanding of permanent data loss risks before creating jobs with deletion enabled.

#### Scenario: User attempts to enable deletion without confirmation
```python
# Given: User is creating a backup job
# When: User fills form with:
#   - Delete source after backup: checked
#   - Deletion mode: "Verify Then Delete"
#   - Confirmation checkbox: NOT checked
# And: User submits form

# Then: Form validation fails
# And: Error message displayed: "You must confirm deletion risks"
# And: Job is NOT created
assert manager.list_jobs() == []  # No job created
```

#### Scenario: User successfully confirms deletion risks
```python
# Given: User is creating a backup job
# When: User fills form with:
#   - Delete source after backup: checked
#   - Confirmation checkbox: checked
# And: User submits form

# Then: Job is created successfully
jobs = manager.list_jobs()
assert len(jobs) == 1
assert jobs[0]['settings']['deletion_confirmed'] == True
```

### Requirement: Mode-specific explanations and warnings display
The system SHALL display clear explanations of each deletion mode and prominent warnings about data loss when deletion is enabled.

#### Scenario: UI shows verify-then-delete explanation
```html
<!-- Given: User selects "Verify Then Delete" mode -->
<!-- When: Form renders deletion settings -->
<!-- Then: Explanation text is displayed -->

<div class="alert alert-info">
  ✅ **Verify-then-delete mode:**
  1. Transfer all files to destination
  2. Verify backup integrity with checksums
  3. Delete source files only if verification passes
  4. Create detailed audit log
</div>
```

#### Scenario: UI shows per-file deletion warning
```html
<!-- Given: User selects "Per-File Deletion" mode -->
<!-- When: Form renders deletion settings -->
<!-- Then: Warning is displayed -->

<div class="alert alert-warning">
  ⚡ **Per-file deletion mode:**
  - Each file is deleted immediately after successful transfer
  - Faster but less safe (no post-transfer verification)
  - Not recommended for critical data
</div>
```

#### Scenario: UI shows permanent deletion warning
```html
<!-- Given: User checks "Delete source after backup" -->
<!-- When: Form shows deletion controls -->
<!-- Then: Prominent warning is displayed -->

<div class="alert alert-danger">
  ⚠️ **WARNING: Source files will be permanently deleted after backup!**
</div>
```
