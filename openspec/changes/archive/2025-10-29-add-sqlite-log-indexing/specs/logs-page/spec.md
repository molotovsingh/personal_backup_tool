## MODIFIED Requirements

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

## ADDED Requirements

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
