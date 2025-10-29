"""
SQLite database management for log indexing
"""
import sqlite3
import threading
from pathlib import Path
from contextlib import contextmanager
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Thread-local storage for database connections
_thread_local = threading.local()


def get_db_connection(db_path: str) -> sqlite3.Connection:
    """
    Get database connection for current thread.
    Connections are thread-local to avoid sqlite threading issues.
    """
    if not hasattr(_thread_local, 'connection') or _thread_local.connection is None:
        conn = sqlite3.connect(db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row  # Enable dict-like access

        # Enable WAL mode for better concurrency
        conn.execute('PRAGMA journal_mode=WAL')
        conn.execute('PRAGMA synchronous=NORMAL')  # Faster writes
        conn.execute('PRAGMA busy_timeout=30000')  # 30 second timeout

        _thread_local.connection = conn
        logger.info(f"Created database connection for thread {threading.current_thread().name}")

    return _thread_local.connection


@contextmanager
def get_db(db_path: str):
    """
    Context manager for database operations.
    Automatically commits on success, rollbacks on error.
    """
    conn = get_db_connection(db_path)
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Database error, rolling back: {e}")
        raise


def initialize_database(db_path: str) -> None:
    """
    Initialize database schema if not exists.
    Creates tables and indexes for log indexing.
    """
    db_file = Path(db_path)

    # Create data directory if it doesn't exist
    db_file.parent.mkdir(parents=True, exist_ok=True)

    with get_db(db_path) as conn:
        cursor = conn.cursor()

        # Create log_entries table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS log_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_id TEXT NOT NULL,
                job_name TEXT,
                timestamp DATETIME NOT NULL,
                level TEXT CHECK(level IN ('ERROR', 'WARNING', 'INFO', 'DEBUG')),
                message TEXT,
                file_path TEXT NOT NULL,
                line_number INTEGER,
                indexed_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Create indexes for performance
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_job_id
            ON log_entries(job_id)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_timestamp
            ON log_entries(timestamp DESC)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_level
            ON log_entries(level)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_indexed
            ON log_entries(indexed_at DESC)
        ''')

        # Create indexer checkpoint table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS indexer_checkpoints (
                file_path TEXT PRIMARY KEY,
                last_position INTEGER NOT NULL,
                last_line_number INTEGER NOT NULL,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Create error_events table (Task 6.5)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS error_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
                severity TEXT CHECK(severity IN ('LOW', 'MEDIUM', 'HIGH', 'CRITICAL')),
                component TEXT NOT NULL,
                error_type TEXT NOT NULL,
                message TEXT NOT NULL,
                details TEXT,
                job_id TEXT,
                job_name TEXT,
                stack_trace TEXT,
                resolved BOOLEAN DEFAULT 0,
                resolved_at DATETIME,
                indexed_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # Create indexes for error_events
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_error_timestamp
            ON error_events(timestamp DESC)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_error_severity
            ON error_events(severity)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_error_component
            ON error_events(component)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_error_job_id
            ON error_events(job_id)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_error_resolved
            ON error_events(resolved, timestamp DESC)
        ''')

        logger.info(f"Database initialized at {db_path}")


def close_connection():
    """Close the thread-local database connection"""
    if hasattr(_thread_local, 'connection') and _thread_local.connection:
        _thread_local.connection.close()
        _thread_local.connection = None
        logger.info(f"Closed database connection for thread {threading.current_thread().name}")
