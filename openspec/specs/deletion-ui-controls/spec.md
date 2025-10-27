# deletion-ui-controls Specification

## Purpose
TBD - created by archiving change add-deletion-to-flask-ui. Update Purpose after archive.
## Requirements
### Requirement: Deletion mode selection in job creation form

The system SHALL provide users the ability to enable source deletion and choose between 'verify_then_delete' and 'per_file' modes when creating a backup job **without UI flicker or race conditions**.

#### Scenario: Deletion checkbox toggles options without flicker

**Given** the job creation form is open
**And** the deletion checkbox is unchecked
**When** the user checks the "Delete source files after successful backup" checkbox
**Then** deletion options SHALL appear smoothly
**And** no UI flicker SHALL occur
**And** deletion mode dropdown SHALL be visible
**And** verification options SHALL be visible
**And** the UI update SHALL use server-driven HTMX (not client-side JavaScript)

#### Scenario: Unchecking deletion checkbox clears options smoothly

**Given** the deletion checkbox is checked
**And** deletion options are visible
**When** the user unchecks the "Delete source files after successful backup" checkbox
**Then** deletion options SHALL disappear smoothly
**And** no UI flicker SHALL occur
**And** the `#deletion-options` container SHALL be empty
**And** the state change SHALL be driven by server response (not JavaScript DOM manipulation)

#### Scenario: Checkbox state correctly sent to server via HTMX

**Given** the deletion checkbox exists in the job creation form
**When** the checkbox is checked
**Then** an HTMX GET request SHALL be sent to `/jobs/deletion-ui`
**And** the request SHALL include parameter `delete_source_after=true`
**And** the request SHALL use `hx-vals` with JavaScript expression `this.checked`
**When** the checkbox is unchecked
**Then** an HTMX GET request SHALL be sent to `/jobs/deletion-ui`
**And** the request SHALL include parameter `delete_source_after=false`
**And** no client-side `onclick` handler SHALL interfere with the request

#### Scenario: Server returns appropriate UI based on checkbox state

**Given** the `/jobs/deletion-ui` endpoint receives a request
**When** the request includes `delete_source_after=true`
**Then** the server SHALL return the deletion options HTML partial
**And** the partial SHALL include deletion mode dropdown
**And** the partial SHALL include confirmation checkbox
**When** the request includes `delete_source_after=false`
**Then** the server SHALL return empty content
**And** the deletion options SHALL not be rendered

#### Scenario: No race condition between HTMX and JavaScript

**Given** the deletion checkbox uses HTMX attributes
**When** the checkbox state changes
**Then** ONLY the HTMX mechanism SHALL control UI updates
**And** NO `onclick` JavaScript handler SHALL exist on the checkbox
**And** NO client-side DOM manipulation SHALL occur
**And** the server SHALL be the single source of truth for UI state

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

