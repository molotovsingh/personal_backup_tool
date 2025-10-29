# logs-page Specification

## Purpose
TBD - created by archiving change migrate-to-flask-app. Update Purpose after archive.
## Requirements
### Requirement: Logs page displays filtered and searchable job logs

The logs page SHALL retrieve and display logs from the SQLite database index for improved performance and search capabilities.

#### Scenario: Database-backed log display

- **GIVEN** logs have been indexed in SQLite database
- **WHEN** the user navigates to the logs page
- **THEN** logs are retrieved from database using efficient queries
- **AND** results are returned in <100ms for up to 100k entries
- **AND** fallback to file reading if database is unavailable
- **AND** display includes all previously specified formatting

#### Scenario: Database-powered search

- **GIVEN** user enters a search term
- **WHEN** search is submitted
- **THEN** SQLite full-text search is used for matching
- **AND** search covers message content and job names
- **AND** results highlight matched terms
- **AND** search completes in <200ms for 1M entries

### Requirement: Export logs to file

The logs page SHALL provide export functionality with multiple format options for filtered logs.

#### Scenario: Export filtered logs with format options

- **GIVEN** logs are displayed (possibly filtered)
- **WHEN** the user clicks "Export" button
- **THEN** a dropdown shows format options: TXT, CSV, JSON
- **AND** selecting a format triggers download
- **AND** export includes ALL logs matching current filters (not just visible on page)
- **AND** filename includes: `logs_[job_name]_[date].[ext]`
- **AND** CSV format includes columns: timestamp, level, job, message
- **AND** JSON format provides structured array of log objects

### Requirement: Manual refresh control

The logs page SHALL provide manual refresh that reloads logs while maintaining user context.

#### Scenario: Manual refresh reloads logs

- **GIVEN** the logs page is displayed with filters/search applied
- **WHEN** the user clicks the "Refresh" button
- **THEN** HTMX reloads logs from server
- **AND** current filter selections are preserved
- **AND** search term is maintained
- **AND** page scrolls to top to show newest entries
- **AND** a brief "Refreshed" toast notification appears

### Requirement: Log level statistics

The logs page SHALL display a summary of log levels for quick health assessment.

#### Scenario: Display log statistics bar

- **GIVEN** logs are loaded on the page
- **WHEN** the page displays or filters change
- **THEN** a statistics bar shows counts: "❌ 5 Errors | ⚠️ 12 Warnings | ℹ️ 143 Info"
- **AND** clicking a count toggles that level's filter
- **AND** counts update based on current search/filter
- **AND** bar uses same color coding as log entries

### Requirement: Enhanced readability

The logs page SHALL format log entries for improved readability and scanability.

#### Scenario: Format timestamps and add line numbers

- **GIVEN** log entries are displayed
- **WHEN** rendering each log line
- **THEN** timestamps are formatted as relative time (e.g., "5 minutes ago") with tooltip showing full timestamp
- **AND** line numbers are shown on the left (starting from 1)
- **AND** job names are visually distinct (bold or colored)
- **AND** long messages wrap properly with indentation

### Requirement: Automatic log indexing

The system SHALL automatically index new log entries into the SQLite database for fast retrieval.

#### Scenario: Background log indexing

- **GIVEN** a job is running and generating logs
- **WHEN** new log lines are written to file
- **THEN** background indexer detects changes within 10 seconds
- **AND** parses entries to extract: timestamp, level, job_id, message
- **AND** inserts parsed entries into database in batches
- **AND** tracks last indexed position to avoid duplicates

#### Scenario: Initial log migration

- **GIVEN** existing log files before database implementation
- **WHEN** system starts with database for first time
- **THEN** migration task indexes all existing log files
- **AND** progress is shown in system logs
- **AND** migration is resumable if interrupted

