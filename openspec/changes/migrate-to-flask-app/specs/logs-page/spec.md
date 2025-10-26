# Spec: Logs Page

## ADDED Requirements

### Requirement: Logs page displays filtered and searchable job logs

The logs page SHALL display job execution logs with filtering by job, search functionality, and export capability.

#### Scenario: Logs page displays all job logs

**Given** the user navigates to the logs page
**When** the page loads
**Then** logs from all jobs are displayed
**And** each log entry shows: timestamp, job name, log level, message
**And** logs are sorted by timestamp (newest first)
**And** maximum 500 log entries are displayed initially
**And** a "Load More" button is available for older logs

#### Scenario: Filter logs by job

**Given** multiple jobs have generated logs
**When** the user selects a specific job from the filter dropdown
**Then** HTMX sends GET request to `/logs?job_id={id}`
**And** only logs for the selected job are displayed
**And** filter dropdown shows the selected job name
**And** "All Jobs" option is available to clear filter

#### Scenario: Search logs by keyword

**Given** logs are displayed on the page
**When** the user enters a search term in the search box
**Then** HTMX sends GET request to `/logs?search={term}` after 500ms debounce
**And** logs containing the search term are displayed
**And** matching text is highlighted in the log entries
**And** search is case-insensitive

### Requirement: Export logs to file

The logs page SHALL provide a way to export filtered logs to a text file.

#### Scenario: Export filtered logs

**Given** logs are displayed (possibly filtered)
**When** the user clicks "Export Logs" button
**Then** a text file download is triggered
**And** the file contains all displayed logs (respecting current filters)
**And** filename includes job name (if filtered) and timestamp
**And** format is: `[timestamp] [job] [level] message` per line

### Requirement: Manual refresh control

The logs page SHALL provide a manual refresh button to reload logs without auto-refresh.

#### Scenario: Manual refresh reloads logs

**Given** the logs page is displayed
**When** the user clicks the "Refresh" button
**Then** HTMX sends GET request to `/logs` with current filters
**And** log entries are reloaded from disk
**And** new log entries (if any) are displayed
**And** scroll position is maintained
