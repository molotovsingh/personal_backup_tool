# job-history-page Specification

## Purpose
TBD - created by archiving change streamline-jobs-page-active-only. Update Purpose after archive.
## Requirements
### Requirement: Job history page displays non-running jobs

The job history page SHALL display all backup jobs with status "completed", "failed", or "paused" in a list with status badges and action buttons (start, delete).

#### ADDED Scenario: History page displays non-running jobs

**Given** the user navigates to `/jobs/history`
**When** the page loads
**Then** all jobs with status != "running" are displayed in a list
**And** each job shows: name, type (rsync/rclone), source, destination, status
**And** status is displayed as a color-coded badge
**And** jobs are sorted by updated timestamp (most recent first)
**And** page heading reads "Job History"
**And** a "← Back to Active Jobs" link is displayed at the top

#### ADDED Scenario: History page shows appropriate controls

**Given** a job with status "completed" or "failed"
**When** the job card is displayed on history page
**Then** a "Start" button is shown (to restart the job)
**And** a "Delete" button is shown
**And** no progress information is displayed

**Given** a job with status "paused"
**When** the job card is displayed on history page
**Then** a "Start" button is shown (to resume the job)
**And** a "Delete" button is shown
**And** progress information from when it was paused may be shown

#### ADDED Scenario: Delete job from history with inline confirmation

**Given** a job is displayed on the history page
**When** the user clicks the "Delete" button
**Then** inline "Delete? [Yes] [No]" buttons are shown
**And** clicking "Yes" sends DELETE request to `/jobs/{id}`
**And** job is removed from storage
**And** job card is removed from the page
**And** clicking "No" returns to normal state
**And** no browser modal or alert is used

#### ADDED Scenario: Restart job from history

**Given** a job with status "completed", "failed", or "paused"
**When** the user clicks the "Start" button on history page
**Then** HTMX sends POST request to `/jobs/{id}/start`
**And** job status changes to "running"
**And** job is removed from history page (since it's now running)
**And** success message is displayed

### Requirement: Job history uses same UI components as main jobs page

The job history page SHALL reuse existing job card templates and styling for consistency.

#### ADDED Scenario: Consistent UI across pages

**Given** the job history page
**When** jobs are rendered
**Then** the same `partials/jobs_list.html` template is used
**And** job cards have identical styling to main jobs page
**And** inline delete confirmation works the same way
**And** HTMX job actions work identically

