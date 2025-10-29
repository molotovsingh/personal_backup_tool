"""
Data access layer for log operations
"""
from typing import List, Dict, Optional, Tuple
from datetime import datetime
import logging
from core.database import get_db
from core.paths import get_db_path

logger = logging.getLogger(__name__)


class LogRepository:
    """Repository for log database operations"""

    def __init__(self):
        self.db_path = str(get_db_path())

    def search_logs(
        self,
        job_id: Optional[str] = None,
        job_name: Optional[str] = None,
        level: Optional[str] = None,
        search_term: Optional[str] = None,
        limit: int = 500,
        offset: int = 0
    ) -> List[Dict]:
        """
        Search logs with optional filters.

        Args:
            job_id: Filter by job ID
            job_name: Filter by job name
            level: Filter by log level (ERROR, WARNING, INFO, DEBUG)
            search_term: Search in message text
            limit: Maximum number of results
            offset: Pagination offset

        Returns:
            List of log entry dicts with keys: job_id, job_name, timestamp, level, message, line_number
        """
        try:
            with get_db(self.db_path) as conn:
                query = """
                    SELECT
                        job_id, job_name, timestamp, level, message,
                        line_number, file_path
                    FROM log_entries
                    WHERE 1=1
                """
                params = []

                if job_id:
                    query += " AND job_id = ?"
                    params.append(job_id)

                if job_name:
                    query += " AND job_name = ?"
                    params.append(job_name)

                if level:
                    query += " AND level = ?"
                    params.append(level)

                if search_term:
                    query += " AND message LIKE ?"
                    params.append(f"%{search_term}%")

                query += " ORDER BY timestamp DESC LIMIT ? OFFSET ?"
                params.extend([limit, offset])

                cursor = conn.execute(query, params)
                rows = cursor.fetchall()

                return [
                    {
                        'job_id': row['job_id'],
                        'job_name': row['job_name'],
                        'timestamp': row['timestamp'],
                        'level': row['level'],
                        'message': row['message'],
                        'line_number': row['line_number'],
                        'file_path': row['file_path']
                    }
                    for row in rows
                ]
        except Exception as e:
            logger.error(f"Error searching logs: {e}")
            return []

    def insert_log_entry(
        self,
        job_id: str,
        job_name: str,
        timestamp: datetime,
        level: str,
        message: str,
        file_path: str,
        line_number: int
    ) -> bool:
        """
        Insert a single log entry.

        Returns:
            True if successful, False otherwise
        """
        try:
            with get_db(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO log_entries
                    (job_id, job_name, timestamp, level, message, file_path, line_number)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (job_id, job_name, timestamp, level, message, file_path, line_number)
                )
            return True
        except Exception as e:
            logger.error(f"Error inserting log entry: {e}")
            return False

    def insert_batch(self, entries: List[Tuple]) -> int:
        """
        Insert multiple log entries in a single transaction.

        Args:
            entries: List of tuples (job_id, job_name, timestamp, level, message, file_path, line_number)

        Returns:
            Number of entries inserted
        """
        if not entries:
            return 0

        try:
            with get_db(self.db_path) as conn:
                conn.executemany(
                    """
                    INSERT INTO log_entries
                    (job_id, job_name, timestamp, level, message, file_path, line_number)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    entries
                )
            logger.info(f"Inserted {len(entries)} log entries")
            return len(entries)
        except Exception as e:
            logger.error(f"Error batch inserting logs: {e}")
            return 0

    def get_log_stats(self) -> Dict[str, int]:
        """
        Get statistics about log levels.

        Returns:
            Dict with counts by level: {'ERROR': 10, 'WARNING': 25, 'INFO': 100}
        """
        try:
            with get_db(self.db_path) as conn:
                cursor = conn.execute(
                    """
                    SELECT level, COUNT(*) as count
                    FROM log_entries
                    GROUP BY level
                    """
                )
                rows = cursor.fetchall()
                return {row['level']: row['count'] for row in rows}
        except Exception as e:
            logger.error(f"Error getting log stats: {e}")
            return {}

    def get_checkpoint(self, file_path: str) -> Optional[Tuple[int, int]]:
        """
        Get the last indexed position for a log file.

        Returns:
            Tuple of (last_position, last_line_number) or None if not found
        """
        try:
            with get_db(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT last_position, last_line_number FROM indexer_checkpoints WHERE file_path = ?",
                    (file_path,)
                )
                row = cursor.fetchone()
                if row:
                    return (row['last_position'], row['last_line_number'])
                return None
        except Exception as e:
            logger.error(f"Error getting checkpoint: {e}")
            return None

    def save_checkpoint(self, file_path: str, position: int, line_number: int) -> bool:
        """
        Save the last indexed position for a log file.

        Returns:
            True if successful, False otherwise
        """
        try:
            with get_db(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO indexer_checkpoints
                    (file_path, last_position, last_line_number, updated_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                    """,
                    (file_path, position, line_number)
                )
            return True
        except Exception as e:
            logger.error(f"Error saving checkpoint: {e}")
            return False
