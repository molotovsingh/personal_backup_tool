"""
Error Event Repository for storing and retrieving error events
"""
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Dict, Any
from core.database import get_db, initialize_database
from core.paths import get_data_dir
from models.error_event import ErrorEvent

logger = logging.getLogger(__name__)


class ErrorEventRepository:
    """Repository for managing error events in SQLite database"""

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize ErrorEventRepository

        Args:
            db_path: Path to SQLite database (defaults to data/events.db)
        """
        if db_path:
            self.db_path = db_path
        else:
            self.db_path = str(Path(get_data_dir()) / "events.db")

        # Initialize database schema
        initialize_database(self.db_path)

    def log_error(self, error_event: ErrorEvent) -> int:
        """
        Log an error event to the database

        Args:
            error_event: ErrorEvent instance to log

        Returns:
            ID of inserted error event
        """
        try:
            with get_db(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    INSERT INTO error_events (
                        timestamp, severity, component, error_type,
                        message, details, job_id, job_name,
                        stack_trace, resolved, resolved_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    error_event.timestamp.isoformat() if isinstance(error_event.timestamp, datetime) else error_event.timestamp,
                    error_event.severity,
                    error_event.component,
                    error_event.error_type,
                    error_event.message,
                    error_event.details,
                    error_event.job_id,
                    error_event.job_name,
                    error_event.stack_trace,
                    1 if error_event.resolved else 0,
                    error_event.resolved_at.isoformat() if error_event.resolved_at else None
                ))

                event_id = cursor.lastrowid
                logger.info(f"Logged error event #{event_id}: {error_event.severity} - {error_event.message}")
                return event_id

        except Exception as e:
            logger.error(f"Failed to log error event: {e}")
            raise

    def get_error(self, error_id: int) -> Optional[ErrorEvent]:
        """
        Get a specific error event by ID

        Args:
            error_id: Error event ID

        Returns:
            ErrorEvent instance or None if not found
        """
        try:
            with get_db(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT id, timestamp, severity, component, error_type,
                           message, details, job_id, job_name, stack_trace,
                           resolved, resolved_at
                    FROM error_events
                    WHERE id = ?
                ''', (error_id,))

                row = cursor.fetchone()
                if row:
                    return self._row_to_error_event(row)

                return None

        except Exception as e:
            logger.error(f"Failed to get error event {error_id}: {e}")
            return None

    def get_recent_errors(self, limit: int = 100, resolved: Optional[bool] = None) -> List[ErrorEvent]:
        """
        Get recent error events

        Args:
            limit: Maximum number of events to return
            resolved: Filter by resolved status (None = all, True = resolved only, False = unresolved only)

        Returns:
            List of ErrorEvent instances
        """
        try:
            with get_db(self.db_path) as conn:
                cursor = conn.cursor()

                if resolved is None:
                    # Get all errors
                    cursor.execute('''
                        SELECT id, timestamp, severity, component, error_type,
                               message, details, job_id, job_name, stack_trace,
                               resolved, resolved_at
                        FROM error_events
                        ORDER BY timestamp DESC
                        LIMIT ?
                    ''', (limit,))
                else:
                    # Filter by resolved status
                    cursor.execute('''
                        SELECT id, timestamp, severity, component, error_type,
                               message, details, job_id, job_name, stack_trace,
                               resolved, resolved_at
                        FROM error_events
                        WHERE resolved = ?
                        ORDER BY timestamp DESC
                        LIMIT ?
                    ''', (1 if resolved else 0, limit))

                rows = cursor.fetchall()
                return [self._row_to_error_event(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to get recent errors: {e}")
            return []

    def get_errors_by_job(self, job_id: str, limit: int = 50) -> List[ErrorEvent]:
        """
        Get error events for a specific job

        Args:
            job_id: Job ID to filter by
            limit: Maximum number of events to return

        Returns:
            List of ErrorEvent instances
        """
        try:
            with get_db(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT id, timestamp, severity, component, error_type,
                           message, details, job_id, job_name, stack_trace,
                           resolved, resolved_at
                    FROM error_events
                    WHERE job_id = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                ''', (job_id, limit))

                rows = cursor.fetchall()
                return [self._row_to_error_event(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to get errors for job {job_id}: {e}")
            return []

    def get_errors_by_severity(self, severity: str, limit: int = 100) -> List[ErrorEvent]:
        """
        Get error events by severity level

        Args:
            severity: Severity level (LOW, MEDIUM, HIGH, CRITICAL)
            limit: Maximum number of events to return

        Returns:
            List of ErrorEvent instances
        """
        try:
            with get_db(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    SELECT id, timestamp, severity, component, error_type,
                           message, details, job_id, job_name, stack_trace,
                           resolved, resolved_at
                    FROM error_events
                    WHERE severity = ?
                    ORDER BY timestamp DESC
                    LIMIT ?
                ''', (severity, limit))

                rows = cursor.fetchall()
                return [self._row_to_error_event(row) for row in rows]

        except Exception as e:
            logger.error(f"Failed to get errors by severity {severity}: {e}")
            return []

    def mark_resolved(self, error_id: int) -> bool:
        """
        Mark an error event as resolved

        Args:
            error_id: Error event ID

        Returns:
            True if successful, False otherwise
        """
        try:
            with get_db(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    UPDATE error_events
                    SET resolved = 1, resolved_at = ?
                    WHERE id = ?
                ''', (datetime.now().isoformat(), error_id))

                logger.info(f"Marked error event #{error_id} as resolved")
                return cursor.rowcount > 0

        except Exception as e:
            logger.error(f"Failed to mark error {error_id} as resolved: {e}")
            return False

    def get_error_stats(self) -> Dict[str, Any]:
        """
        Get error statistics

        Returns:
            Dictionary with error statistics
        """
        try:
            with get_db(self.db_path) as conn:
                cursor = conn.cursor()

                # Total errors
                cursor.execute('SELECT COUNT(*) FROM error_events')
                total = cursor.fetchone()[0]

                # Unresolved errors
                cursor.execute('SELECT COUNT(*) FROM error_events WHERE resolved = 0')
                unresolved = cursor.fetchone()[0]

                # By severity
                cursor.execute('''
                    SELECT severity, COUNT(*) as count
                    FROM error_events
                    WHERE resolved = 0
                    GROUP BY severity
                ''')
                by_severity = {row[0]: row[1] for row in cursor.fetchall()}

                # Recent errors (last 24 hours)
                cursor.execute('''
                    SELECT COUNT(*)
                    FROM error_events
                    WHERE datetime(timestamp) >= datetime('now', '-1 day')
                ''')
                recent_24h = cursor.fetchone()[0]

                return {
                    'total': total,
                    'unresolved': unresolved,
                    'resolved': total - unresolved,
                    'by_severity': by_severity,
                    'recent_24h': recent_24h
                }

        except Exception as e:
            logger.error(f"Failed to get error stats: {e}")
            return {
                'total': 0,
                'unresolved': 0,
                'resolved': 0,
                'by_severity': {},
                'recent_24h': 0
            }

    def delete_old_errors(self, days: int = 30) -> int:
        """
        Delete resolved errors older than specified days

        Args:
            days: Number of days to keep (default 30)

        Returns:
            Number of errors deleted
        """
        try:
            with get_db(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute('''
                    DELETE FROM error_events
                    WHERE resolved = 1
                    AND datetime(timestamp) < datetime('now', '-' || ? || ' days')
                ''', (days,))

                deleted = cursor.rowcount
                logger.info(f"Deleted {deleted} old resolved errors (older than {days} days)")
                return deleted

        except Exception as e:
            logger.error(f"Failed to delete old errors: {e}")
            return 0

    def _row_to_error_event(self, row) -> ErrorEvent:
        """
        Convert database row to ErrorEvent instance

        Args:
            row: SQLite row object

        Returns:
            ErrorEvent instance
        """
        timestamp = row['timestamp']
        if timestamp and isinstance(timestamp, str):
            timestamp = datetime.fromisoformat(timestamp)

        resolved_at = row['resolved_at']
        if resolved_at and isinstance(resolved_at, str):
            resolved_at = datetime.fromisoformat(resolved_at)

        return ErrorEvent(
            event_id=row['id'],
            timestamp=timestamp,
            severity=row['severity'],
            component=row['component'],
            error_type=row['error_type'],
            message=row['message'],
            details=row['details'],
            job_id=row['job_id'],
            job_name=row['job_name'],
            stack_trace=row['stack_trace'],
            resolved=bool(row['resolved']),
            resolved_at=resolved_at
        )


# Global singleton instance
_error_repo = None


def get_error_repository() -> ErrorEventRepository:
    """
    Get singleton ErrorEventRepository instance

    Returns:
        ErrorEventRepository instance
    """
    global _error_repo
    if _error_repo is None:
        _error_repo = ErrorEventRepository()
    return _error_repo
