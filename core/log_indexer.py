"""
Background service for indexing log files into SQLite database
"""
import asyncio
import logging
from pathlib import Path
from datetime import datetime
from typing import List, Tuple
import re

from core.log_repository import LogRepository
from core.paths import get_logs_dir, get_db_path
from core.database import initialize_database
from core.job_manager import JobManager

logger = logging.getLogger(__name__)


def parse_log_level(line: str) -> str:
    """Extract log level from log line"""
    level_pattern = r'\b(ERROR|FAIL|FAILED|WARN|WARNING|INFO|DEBUG|SUCCESS|COMPLETED)\b'
    match = re.search(level_pattern, line, re.IGNORECASE)

    if match:
        level = match.group(1).upper()
        if level in ['WARN', 'WARNING']:
            return 'WARNING'
        elif level in ['FAIL', 'FAILED']:
            return 'ERROR'
        elif level in ['SUCCESS', 'COMPLETED']:
            return 'INFO'
        return level

    if re.search(r'\b(error|fail|exception|critical)\b', line, re.IGNORECASE):
        return 'ERROR'

    return 'INFO'


def parse_timestamp(line: str) -> datetime:
    """Extract and parse timestamp from log line"""
    timestamp_patterns = [
        r'\[(\d{4}[-/]\d{2}[-/]\d{2}\s+\d{2}:\d{2}:\d{2})\]',
        r'^(\d{4}[-/]\d{2}[-/]\d{2}\s+\d{2}:\d{2}:\d{2})',
    ]

    for pattern in timestamp_patterns:
        match = re.search(pattern, line)
        if match:
            timestamp_str = match.group(1)
            try:
                if '/' in timestamp_str:
                    return datetime.strptime(timestamp_str, '%Y/%m/%d %H:%M:%S')
                else:
                    return datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
            except:
                pass

    # Fallback to current time if no timestamp found
    return datetime.now()


class LogIndexer:
    """Background service to index log files into database"""

    def __init__(self, interval: int = 30):
        """
        Initialize log indexer.

        Args:
            interval: Seconds between index runs (default: 30)
        """
        self.interval = interval
        self.repository = LogRepository()
        self.logs_dir = get_logs_dir()
        self.db_path = str(get_db_path())
        self.running = False
        self.task = None

        # Initialize database on startup
        initialize_database(self.db_path)
        logger.info(f"LogIndexer initialized with {interval}s interval")

    async def start(self):
        """Start the background indexing task"""
        if self.running:
            logger.warning("LogIndexer already running")
            return

        self.running = True
        self.task = asyncio.create_task(self._index_loop())
        logger.info("LogIndexer started")

    async def stop(self):
        """Stop the background indexing task"""
        if not self.running:
            return

        self.running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass
        logger.info("LogIndexer stopped")

    async def _index_loop(self):
        """Main indexing loop"""
        while self.running:
            try:
                await self._index_all_logs()
            except Exception as e:
                logger.error(f"Error in indexing loop: {e}")

            # Wait for next interval
            await asyncio.sleep(self.interval)

    async def _index_all_logs(self):
        """Index all log files in the logs directory"""
        if not self.logs_dir.exists():
            return

        log_files = list(self.logs_dir.glob('*.log'))
        if not log_files:
            return

        # Get job manager to map job IDs to names
        try:
            manager = JobManager()
            jobs = manager.list_jobs()
            job_id_to_name = {job['id']: job['name'] for job in jobs}
        except:
            job_id_to_name = {}

        for log_file in log_files:
            try:
                await self._index_log_file(log_file, job_id_to_name)
            except Exception as e:
                logger.error(f"Error indexing {log_file}: {e}")

    async def _index_log_file(self, log_file: Path, job_id_to_name: dict):
        """Index a single log file"""
        file_path = str(log_file)

        # Extract job ID from filename (rsync_<job_id>.log or rclone_<job_id>.log)
        filename = log_file.stem
        parts = filename.split('_', 1)
        job_id = parts[1] if len(parts) > 1 else filename
        job_name = job_id_to_name.get(job_id, job_id)

        # Get last indexed position
        checkpoint = self.repository.get_checkpoint(file_path)
        if checkpoint:
            last_position, last_line_number = checkpoint
        else:
            last_position, last_line_number = 0, 0

        # Read new lines from file
        try:
            with open(log_file, 'r') as f:
                # Seek to last position
                f.seek(last_position)

                new_lines = f.readlines()
                if not new_lines:
                    return

                # Parse and batch insert
                entries = []
                current_line_number = last_line_number

                for line in new_lines:
                    if not line.strip():
                        continue

                    current_line_number += 1
                    timestamp = parse_timestamp(line)
                    level = parse_log_level(line)
                    message = line.strip()

                    entries.append((
                        job_id,
                        job_name,
                        timestamp,
                        level,
                        message,
                        file_path,
                        current_line_number
                    ))

                    # Batch insert every 100 entries
                    if len(entries) >= 100:
                        self.repository.insert_batch(entries)
                        entries = []

                # Insert remaining entries
                if entries:
                    self.repository.insert_batch(entries)

                # Save checkpoint
                new_position = f.tell()
                self.repository.save_checkpoint(file_path, new_position, current_line_number)

                logger.debug(f"Indexed {current_line_number - last_line_number} new lines from {log_file.name}")

        except Exception as e:
            logger.error(f"Error reading log file {log_file}: {e}")
