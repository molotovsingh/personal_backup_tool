# deletion-ui-controls Specification

## Purpose
TBD - created by archiving change add-deletion-to-flask-ui. Update Purpose after archive.
## Requirements
### Requirement: Deletion mode selection in job creation form

The system SHALL present deletion options by default when the job creation form first renders, allow users to toggle them off/on without flicker, and keep all UI updates server-driven (HTMX or server-rendered).

#### Scenario: Deletion options visible by default on form load
**Given** the job creation form is open
**When** the form completes initial render
**Then** the deletion toggle SHALL be checked
**And** the `#deletion-options` region SHALL be populated with the deletion options partial
**And** the default deletion mode SHALL be `verify_then_delete`
**And** the confirmation checkbox SHALL be present
**And** the UI update SHALL be server-driven (server render OR HTMX)
**And** if HTMX is used, the component SHALL issue a GET to `/jobs/deletion-ui` with `delete_source_after=true` automatically on load

#### Scenario: Unchecking deletion checkbox clears options smoothly
**Given** the deletion checkbox is checked
**And** deletion options are visible
**When** the user unchecks the "Delete source files after successful backup" checkbox
**Then** deletion options SHALL disappear smoothly
**And** no UI flicker SHALL occur
**And** the `#deletion-options` container SHALL be empty
**And** the state change SHALL be driven by server response (not client-side DOM manipulation)

#### Scenario: Rechecking shows options without flicker
**Given** the deletion checkbox is unchecked
**When** the user checks the checkbox
**Then** the deletion options SHALL appear smoothly
**And** no UI flicker SHALL occur

#### Scenario: Checkbox state correctly sent to server via HTMX
**Given** the deletion checkbox exists in the job creation form
**When** the checkbox is checked
**Then** an HTMX GET request SHALL be sent to `/jobs/deletion-ui`
**And** the request SHALL include parameter `delete_source_after=true`
**And** for initial load this MAY be triggered by `hx-trigger="load"`
**When** the checkbox is unchecked
**Then** an HTMX GET request SHALL be sent to `/jobs/deletion-ui`
**And** the request SHALL include parameter `delete_source_after=false`

#### Scenario: No race condition between HTMX and JavaScript
**Given** the deletion checkbox uses HTMX attributes
**When** the checkbox state changes or initial load occurs
**Then** ONLY the HTMX mechanism or server render SHALL control UI updates
**And** NO client-side DOM manipulation SHALL occur
**And** the server SHALL be the single source of truth for UI state

### Requirement: Explicit confirmation required before enabling deletion
The system SHALL require users to explicitly confirm understanding of permanent data loss risks before creating jobs with deletion enabled, WITHOUT using blocking browser dialogs.

#### Scenario: User attempts to enable deletion without confirmation
**Given** deletion is enabled in the form
**And** the confirmation checkbox is NOT checked
**When** the user submits the form
**Then** form validation SHALL fail
**And** an inline message near the confirmation control OR a server flash message SHALL be displayed
**And** NO browser `alert`, `confirm`, or `prompt` SHALL be used
**And** the job SHALL NOT be created

#### Scenario: User successfully confirms deletion risks
**Given** deletion is enabled in the form
**And** the confirmation checkbox is checked
**When** the user submits the form
**Then** the job SHALL be created successfully
**And** the job settings SHALL record `deletion_confirmed = true`

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

