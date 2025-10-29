# data-persistence Specification

## Purpose
TBD - created by archiving change add-sqlite-log-indexing. Update Purpose after archive.
## Requirements
### Requirement: SQLite database management

The system SHALL provide a SQLite database for persistent storage of indexed log entries and future job data.

#### Scenario: Database initialization

- **GIVEN** the application starts
- **WHEN** no database exists
- **THEN** database file is created at ~/backup-manager/backup_manager.db
- **AND** schema migrations are applied automatically
- **AND** WAL mode is enabled for concurrent access
- **AND** appropriate indexes are created

#### Scenario: Connection management

- **GIVEN** multiple components need database access
- **WHEN** connections are requested
- **THEN** connection pool provides up to 5 concurrent connections
- **AND** connections are recycled after 300 seconds
- **AND** failed connections retry with exponential backoff
- **AND** database locks are handled gracefully

### Requirement: Data retention policies

The system SHALL enforce retention policies to manage database size and performance.

#### Scenario: Log entry retention

- **GIVEN** log entries accumulate in database
- **WHEN** retention job runs daily at 2 AM
- **THEN** log entries older than 90 days are deleted
- **AND** database is vacuumed to reclaim space
- **AND** deletion is logged for audit
- **AND** raw log files follow separate 30-day retention

#### Scenario: Database maintenance

- **GIVEN** database requires optimization
- **WHEN** maintenance window occurs (daily at 3 AM)
- **THEN** ANALYZE is run to update statistics
- **AND** VACUUM is run if fragmentation >20%
- **AND** database is backed up to ~/backup-manager/backups/
- **AND** old backups >7 days are removed

### Requirement: Data access layer

The system SHALL provide a repository pattern for database operations with proper abstraction.

#### Scenario: Repository pattern implementation

- **GIVEN** application needs to access log data
- **WHEN** queries are executed
- **THEN** LogRepository class handles all database operations
- **AND** SQL injection is prevented via parameterized queries
- **AND** results are mapped to domain objects
- **AND** errors are logged and handled gracefully

#### Scenario: Transaction support

- **GIVEN** multiple related database operations
- **WHEN** operations need atomicity
- **THEN** transactions ensure all-or-nothing execution
- **AND** rollback occurs on any error
- **AND** isolation level prevents dirty reads
- **AND** deadlocks are detected and retried

