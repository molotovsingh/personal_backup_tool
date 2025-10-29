## Why
Current log storage uses only flat files which requires reading entire files for searching and filtering. Adding SQLite indexing will enable fast searches, better performance with large logs, and lay the foundation for migrating job storage from YAML to database.

## What Changes
- Add SQLite database for log entry indexing
- Create background task to index log files into database
- Implement database-backed search and filtering
- Add log retention policies (30 days files, 90 days indexed)
- Create data access layer for database operations
- **BREAKING**: Log search will require database initialization on first run

## Impact
- Affected specs: logs-page, data-persistence (new)
- Affected code: New modules for database management, log indexing service, updated logs.py to use database
