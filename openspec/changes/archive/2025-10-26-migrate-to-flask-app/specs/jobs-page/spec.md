# Spec: Jobs Page

## ADDED Requirements

### Requirement: Jobs page displays all jobs with status and controls

The jobs page SHALL display all backup jobs in a list with status badges, progress information, and action buttons (start, pause, delete).

#### Scenario: Jobs list displays all jobs

**Given** the user navigates to the jobs page
**When** the page loads
**Then** all jobs are displayed in a list
**And** each job shows: name, type (rsync/rclone), source, destination, status
**And** status is displayed as a color-coded badge
**And** jobs are sorted by updated timestamp (most recent first)

#### Scenario: Job card shows appropriate controls based on status

**Given** a job with status "pending"
**When** the job card is displayed
**Then** an enabled "Start" button is shown
**And** a "Delete" button is shown
**And** no "Pause" button is shown

**Given** a job with status "running"
**When** the job card is displayed
**Then** an enabled "Pause" button is shown
**And** a "Delete" button is shown
**And** progress bar, speed, and ETA are displayed
**And** no "Start" button is shown

**Given** a job with status "completed"
**When** the job card is displayed
**Then** a "✓ Completed" badge is shown
**And** a "Delete" button is shown
**And** no action buttons (Start/Pause) are shown

### Requirement: Create new job form with validation

The jobs page SHALL provide a form to create new backup jobs with source/destination validation and optional settings.

#### Scenario: Create job form displays all fields

**Given** the user clicks "New Job" button
**When** the create job form is displayed
**Then** fields are shown for: name, type (rsync/rclone), source, destination
**And** optional fields are shown for: bandwidth limit, deletion settings
**And** source and destination have path browser buttons
**And** form validation is applied client-side (HTML5 + HTMX)

#### Scenario: Job creation validates paths

**Given** the user fills out the create job form
**When** the user submits the form
**Then** source path is validated (must exist)
**And** destination path is validated (must be writable)
**And** if validation fails, inline error messages are shown
**And** if validation passes, job is created and added to the list
**And** success message is displayed

### Requirement: Job actions trigger via HTMX

The jobs page SHALL use HTMX for all job actions (start, pause, delete) to avoid full page reloads.

#### Scenario: Start job via HTMX

**Given** a job with status "pending" or "paused"
**When** the user clicks the "Start" button
**Then** HTMX sends POST request to `/jobs/{id}/start`
**And** Flask starts the job and returns updated HTML fragment
**And** HTMX swaps the job card with updated status
**And** no full page reload occurs
**And** success message is displayed inline

#### Scenario: Delete job with confirmation

**Given** any job is displayed
**When** the user clicks the "Delete" button
**Then** a confirmation modal is shown (HTMX + HTML dialog)
**And** if user confirms, HTMX sends DELETE request to `/jobs/{id}`
**And** job is removed from storage
**And** job card is removed from the page
**And** success message is displayed

### Requirement: Real-time progress updates via WebSocket

Running jobs SHALL display live progress updates via WebSocket without polling.

#### Scenario: Job progress updates in real-time

**Given** a job is running
**When** the job makes progress
**Then** Flask-SocketIO emits progress event with: bytes_transferred, percent, speed, ETA
**And** JavaScript receives the event
**And** progress bar is updated smoothly
**And** speed and ETA text are updated
**And** updates occur without HTMX polling (more efficient)

#### Scenario: Job status change reflected immediately

**Given** a job is running
**When** the job completes or fails
**Then** WebSocket emits status change event
**And** JavaScript updates the job card UI
**And** status badge changes color
**And** action buttons change (e.g., show "Completed" instead of "Pause")
