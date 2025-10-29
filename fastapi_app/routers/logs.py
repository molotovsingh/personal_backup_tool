"""
Logs routes (FastAPI)
"""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, Response
from core.job_manager import JobManager
from core.log_repository import LogRepository
import os
from pathlib import Path
from datetime import datetime
import re
import logging

# Import FlaskCompatRequest, templates, and helpers from main app
from fastapi_app import FlaskCompatRequest, templates, create_flash_getter

router = APIRouter()
logger = logging.getLogger(__name__)

# Initialize repository (will be used if database is available)
try:
    log_repository = LogRepository()
    USE_DATABASE = True
    logger.info("LogRepository initialized - using database for logs")
except Exception as e:
    log_repository = None
    USE_DATABASE = False
    logger.warning(f"LogRepository failed to initialize - falling back to file reading: {e}")


def parse_log_level(line):
    """Extract log level from log line"""
    # Match common log level patterns: ERROR, WARN/WARNING, INFO, DEBUG
    level_pattern = r'\b(ERROR|FAIL|FAILED|WARN|WARNING|INFO|DEBUG|SUCCESS|COMPLETED)\b'
    match = re.search(level_pattern, line, re.IGNORECASE)

    if match:
        level = match.group(1).upper()
        # Normalize variants
        if level in ['WARN', 'WARNING']:
            return 'WARNING'
        elif level in ['FAIL', 'FAILED']:
            return 'ERROR'
        elif level in ['SUCCESS', 'COMPLETED']:
            return 'INFO'
        return level

    # Heuristic: lines with "error", "fail", "exception" are likely errors
    if re.search(r'\b(error|fail|exception|critical)\b', line, re.IGNORECASE):
        return 'ERROR'

    # Default to INFO for regular log lines
    return 'INFO'


def parse_timestamp(line):
    """Extract and format timestamp from log line"""
    # Match common timestamp formats:
    # [2025-10-27 19:48:54]
    # 2025-10-27 19:48:54
    # [2025/10/27 19:48:54]
    timestamp_patterns = [
        r'\[(\d{4}[-/]\d{2}[-/]\d{2}\s+\d{2}:\d{2}:\d{2})\]',
        r'^(\d{4}[-/]\d{2}[-/]\d{2}\s+\d{2}:\d{2}:\d{2})',
    ]

    for pattern in timestamp_patterns:
        match = re.search(pattern, line)
        if match:
            timestamp_str = match.group(1)
            try:
                # Parse and reformat timestamp
                if '/' in timestamp_str:
                    dt = datetime.strptime(timestamp_str, '%Y/%m/%d %H:%M:%S')
                else:
                    dt = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                return dt.strftime('%Y-%m-%d %H:%M:%S')
            except:
                return timestamp_str

    return None


def read_log_file(log_path, max_lines=500):
    """Read last N lines from a log file efficiently"""
    try:
        # Check file size - skip very large files (>5MB) when reading all logs
        file_size = os.path.getsize(log_path)
        if file_size > 5 * 1024 * 1024:  # 5MB
            return [f"[Log file too large ({file_size / 1024 / 1024:.1f}MB) - showing only last {max_lines} lines]"]

        with open(log_path, 'r') as f:
            lines = f.readlines()
            return lines[-max_lines:] if len(lines) > max_lines else lines
    except Exception as e:
        return []


def get_logs_from_database(job_filter=None, search_term=None, level_filter=None, max_lines=500):
    """
    Get logs from database.

    Returns list of log dicts or None if database unavailable.
    """
    if not USE_DATABASE or not log_repository:
        return None

    try:
        # Search database
        results = log_repository.search_logs(
            job_name=job_filter if job_filter and job_filter != 'all' else None,
            level=level_filter,
            search_term=search_term,
            limit=max_lines
        )

        # Transform to match expected format
        logs = []
        for row in results:
            logs.append({
                'job_name': row['job_name'],
                'job_id': row['job_id'],
                'line': row['message'],
                'level': row['level'],
                'timestamp': row['timestamp'],
                'line_number': row['line_number'],
                'highlighted': search_term if search_term else None
            })

        logger.debug(f"Retrieved {len(logs)} logs from database")
        return logs

    except Exception as e:
        logger.error(f"Error querying database: {e}")
        return None


def get_all_logs(logs_dir, job_filter=None, search_term=None, level_filter=None, max_lines=500):
    """Get logs from all job log files (fallback when database unavailable)"""
    logs_path = Path(logs_dir)
    all_logs = []

    if not logs_path.exists():
        return []

    # Get all log files
    log_files = sorted(logs_path.glob('*.log'), key=lambda x: x.stat().st_mtime, reverse=True)

    # Get job manager to map job IDs to names
    manager = JobManager()
    jobs = manager.list_jobs()
    job_id_to_name = {job['id']: job['name'] for job in jobs}

    line_number = 1
    for log_file in log_files:
        log_filename = log_file.stem  # filename without extension (e.g., "rsync_<job_id>")

        # Extract job ID from log filename (format: rsync_<job_id> or rclone_<job_id>)
        parts = log_filename.split('_', 1)
        job_id = parts[1] if len(parts) > 1 else log_filename
        job_name = job_id_to_name.get(job_id, log_filename)  # Map ID to name, or use filename

        # Apply job filter (match against job ID or job name)
        if job_filter and job_filter != 'all':
            if job_filter != job_id and job_filter != job_name:
                continue

        # Read log lines
        lines = read_log_file(log_file, max_lines)

        for line in lines:
            # Parse log level
            level = parse_log_level(line)

            # Apply level filter
            if level_filter and level_filter != 'all' and level != level_filter:
                continue

            # Apply search filter
            if search_term and search_term.lower() not in line.lower():
                continue

            # Parse timestamp
            timestamp = parse_timestamp(line)

            # Parse log line (with metadata)
            all_logs.append({
                'job_name': job_name,  # Use the mapped job name, not the filename
                'job_id': job_id,
                'line': line.strip(),
                'level': level,
                'timestamp': timestamp,
                'line_number': line_number,
                'highlighted': search_term if search_term else None
            })
            line_number += 1

    return all_logs[-max_lines:]  # Return most recent


@router.get("/", response_class=HTMLResponse)
async def index(request: Request, job_id: str = 'all', search: str = '', level: str = 'all'):
    """Logs page"""
    # Get job list for filter dropdown
    manager = JobManager()
    jobs = manager.list_jobs()

    # Try database first, fall back to file reading
    logs = get_logs_from_database(
        job_filter=job_id,
        search_term=search if search else None,
        level_filter=level if level != 'all' else None
    )

    # Fallback to file reading if database unavailable
    if logs is None:
        from core.paths import get_logs_dir
        logs_dir = get_logs_dir()
        logs = get_all_logs(logs_dir, job_id, search if search else None, level if level != 'all' else None)
        logger.debug("Using file-based log reading (database unavailable)")

    # If HTMX request, return partial
    if request.headers.get('HX-Request'):
        return templates.TemplateResponse('partials/logs_list.html', {
            'request': FlaskCompatRequest(request),
            'logs': logs,
            'search_term': search,
            'selected_level': level,
            'get_flashed_messages': create_flash_getter(request.session)
        })

    return templates.TemplateResponse('logs.html', {
        'request': FlaskCompatRequest(request),
        'logs': logs,
        'jobs': jobs,
        'selected_job': job_id,
        'selected_level': level,
        'search_term': search,
        'get_flashed_messages': create_flash_getter(request.session)
    })


@router.get("/export")
async def export(request: Request, job_id: str = 'all', search: str = ''):
    """Export logs as text file"""
    # Get system logs directory
    from core.paths import get_logs_dir
    logs_dir = get_logs_dir()

    # Get logs (no line limit for export)
    logs = get_all_logs(logs_dir, job_id, search if search else None, max_lines=10000)

    # Format for export
    export_lines = []
    for log in logs:
        export_lines.append(f"[{log['job_name']}] {log['line']}")

    export_content = "\n".join(export_lines)

    # Generate filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"backup_logs_{job_id}_{timestamp}.txt"

    return Response(
        content=export_content,
        media_type='text/plain',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )
