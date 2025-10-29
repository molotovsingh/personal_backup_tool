## Context
The current system stores logs as flat text files and jobs in YAML. This works but has scalability limits. As log volumes grow, searching and filtering becomes slow. This change adds SQLite for log indexing as a first step toward full database-backed storage.

## Goals / Non-Goals
- Goals:
  - Fast log searching and filtering via indexes
  - Structured log data for analytics
  - Foundation for future job storage migration
  - Maintain backward compatibility with existing log files
  - Zero configuration database setup

- Non-Goals:
  - Real-time log streaming
  - Distributed database or clustering
  - Log aggregation from external sources
  - Immediate migration of job storage (future phase)

## Decisions

### Decision: SQLite over other databases
- SQLite chosen for zero-configuration, embedded nature
- No external dependencies or services to manage
- Sufficient for single-node backup manager
- Alternatives considered: PostgreSQL (overkill), MongoDB (unnecessary complexity)

### Decision: Hybrid storage approach
- Keep raw log files as source of truth
- Database as index/cache for fast queries
- Rationale: Maintains file-based debugging, database corruption recovery

### Decision: Schema Design
```sql
-- Core log entries table
CREATE TABLE log_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    job_id TEXT NOT NULL,
    job_name TEXT,
    timestamp DATETIME NOT NULL,
    level TEXT CHECK(level IN ('ERROR', 'WARNING', 'INFO', 'DEBUG')),
    message TEXT,
    file_path TEXT NOT NULL,
    line_number INTEGER,
    indexed_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_job_id ON log_entries(job_id);
CREATE INDEX idx_timestamp ON log_entries(timestamp);
CREATE INDEX idx_level ON log_entries(level);
CREATE INDEX idx_indexed ON log_entries(indexed_at);

-- Full-text search
CREATE VIRTUAL TABLE log_search USING fts5(
    message, 
    content=log_entries, 
    content_rowid=id
);

-- Future: Jobs table (prepared but not migrated yet)
CREATE TABLE jobs (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL UNIQUE,
    source TEXT NOT NULL,
    destination TEXT NOT NULL,
    type TEXT CHECK(type IN ('rsync', 'rclone')),
    status TEXT,
    settings JSON,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

### Decision: Indexing Strategy
- Watch log directory for changes using asyncio
- Index new entries every 10 seconds (configurable)
- Track last indexed position per file
- Batch inserts of 100 entries for performance

### Decision: Connection Management
- Use WAL mode for concurrent reads during writes
- Connection pool with 5 connections
- 30-second timeout for long queries
- Automatic retry on SQLITE_BUSY

## Risks / Trade-offs
- Database corruption risk → Keep raw files, daily backups
- Indexing lag → 10-second delay acceptable for non-realtime logs
- Storage overhead → ~50% increase, acceptable for query speed
- Migration complexity → Gradual rollout with feature flags

## Migration Plan
1. Deploy database schema alongside existing system
2. Background index existing logs (one-time job)
3. Start indexing new logs continuously
4. Update UI to query database with file fallback
5. Monitor performance and storage
6. Future: Migrate jobs to database (separate change)

## Performance Targets
- Search 1M log entries in <100ms
- Index 1000 entries/second
- Database size <2x raw log size
- Support 10 concurrent queries

## Open Questions
- Should we compress old log entries in database?
- Do we need replication for backup?
- Should search support regex patterns?
