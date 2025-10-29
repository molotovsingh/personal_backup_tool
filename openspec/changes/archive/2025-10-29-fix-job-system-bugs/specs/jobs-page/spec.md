## MODIFIED Requirements

### Requirement: Jobs page provides real-time job management interface

The jobs page SHALL provide a reliable interface for creating, monitoring, and controlling backup jobs with proper error handling and state consistency.

#### Scenario: Job status queries do not modify state

- **GIVEN** a job is running or completed
- **WHEN** the UI queries job status via API
- **THEN** the query returns current state without modifications
- **AND** no side effects occur (no status changes, no engine cleanup)
- **AND** response time is under 10ms
- **AND** concurrent queries return consistent results

#### Scenario: WebSocket reconnects with exponential backoff

- **GIVEN** the WebSocket connection is lost
- **WHEN** the client attempts to reconnect
- **THEN** reconnection uses exponential backoff starting at 1 second
- **AND** maximum delay is capped at 30 seconds
- **AND** maximum retry attempts is 10
- **AND** connection status indicator shows current state
- **AND** after max retries, fallback to manual refresh mode

#### Scenario: Job completion updates only affected card

- **GIVEN** multiple jobs are displayed and one completes
- **WHEN** WebSocket sends completion notification
- **THEN** only the completed job's card is updated
- **AND** page does NOT reload
- **AND** other running jobs continue updating
- **AND** user's scroll position is maintained
- **AND** form state (if open) is preserved

#### Scenario: Deletion checkbox synchronized with options

- **GIVEN** the create job form is displayed
- **WHEN** user checks "Delete source files" checkbox
- **THEN** deletion options panel loads via HTMX
- **AND** checkbox state is preserved during panel load
- **AND** unchecking clears the options panel
- **AND** form reset clears both checkbox and options
- **AND** validation ensures deletion_confirmed matches delete_source_after

## ADDED Requirements

### Requirement: Error visibility and recovery

The system SHALL provide clear error notifications and recovery mechanisms for job failures.

#### Scenario: Background errors shown to user

- **GIVEN** a job operation fails in background
- **WHEN** the error occurs
- **THEN** error is logged with full context
- **AND** user notification appears in UI (toast or banner)
- **AND** error details are available in logs page
- **AND** recovery action is suggested when possible

#### Scenario: Connection status indicator

- **GIVEN** the jobs page uses WebSocket for updates
- **WHEN** the page is displayed
- **THEN** connection status indicator shows: Connected (green), Reconnecting (yellow), Disconnected (red)
- **AND** indicator updates within 1 second of state change
- **AND** hover tooltip shows details (retry count, next attempt)

### Requirement: Job lifecycle management

The system SHALL properly manage job engine lifecycle to prevent memory leaks.

#### Scenario: Automatic engine cleanup

- **GIVEN** job engines are tracked in memory
- **WHEN** a job stops, fails, or completes
- **THEN** engine is marked for cleanup
- **AND** cleanup occurs within 30 seconds
- **AND** final progress is saved before cleanup
- **AND** cleanup is logged for debugging

#### Scenario: Memory pressure handling

- **GIVEN** system tracks multiple job engines
- **WHEN** memory usage exceeds threshold (100MB or 100 engines)
- **THEN** oldest stopped engines are cleaned first
- **AND** running jobs are never affected
- **AND** warning is logged about memory pressure

## MODIFIED Requirements

### Requirement: Job data persistence

The system SHALL ensure reliable and consistent storage of job data without corruption.

#### Scenario: Atomic YAML writes with locking

- **GIVEN** multiple threads need to update jobs.yaml
- **WHEN** a write operation occurs
- **THEN** file lock is acquired before write
- **AND** write uses atomic rename operation
- **AND** backup is created before modification
- **AND** lock is released within 100ms
- **AND** concurrent writes queue and retry

#### Scenario: Final progress always saved

- **GIVEN** a job is running and approaching completion
- **WHEN** job transitions to completed/failed state
- **THEN** final progress is saved before status change
- **AND** progress includes all metrics (bytes, files, deletion stats)
- **AND** save is confirmed before WebSocket notification
- **AND** no progress updates are lost
