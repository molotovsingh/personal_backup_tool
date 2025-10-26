"""
Logs routes
"""
from flask import Blueprint, render_template, request, Response
from core.job_manager import JobManager
import os
from pathlib import Path
from datetime import datetime

logs_bp = Blueprint('logs', __name__)


def read_log_file(log_path, max_lines=500):
    """Read last N lines from a log file"""
    try:
        with open(log_path, 'r') as f:
            lines = f.readlines()
            return lines[-max_lines:] if len(lines) > max_lines else lines
    except Exception as e:
        return []


def get_all_logs(logs_dir, job_filter=None, search_term=None, max_lines=500):
    """Get logs from all job log files"""
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
            # Apply search filter
            if search_term and search_term.lower() not in line.lower():
                continue

            # Parse log line (simple format)
            all_logs.append({
                'job_name': job_name,  # Use the mapped job name, not the filename
                'job_id': job_id,
                'line': line.strip(),
                'highlighted': search_term if search_term else None
            })

    return all_logs[-max_lines:]  # Return most recent


@logs_bp.route('/')
def index():
    """Logs page"""
    # Get query parameters
    job_filter = request.args.get('job_id', 'all')
    search_term = request.args.get('search', '')

    # Get job list for filter dropdown
    manager = JobManager()
    jobs = manager.list_jobs()

    # Get system logs directory
    from flask_app.config import Config
    logs_dir = Config.LOGS_DIR

    # Get logs
    logs = get_all_logs(logs_dir, job_filter, search_term if search_term else None)

    # If HTMX request, return partial
    if request.headers.get('HX-Request'):
        return render_template('partials/logs_list.html',
                              logs=logs,
                              search_term=search_term)

    return render_template('logs.html',
                          logs=logs,
                          jobs=jobs,
                          selected_job=job_filter,
                          search_term=search_term)


@logs_bp.route('/export')
def export():
    """Export logs as text file"""
    # Get query parameters
    job_filter = request.args.get('job_id', 'all')
    search_term = request.args.get('search', '')

    # Get system logs directory
    from flask_app.config import Config
    logs_dir = Config.LOGS_DIR

    # Get logs (no line limit for export)
    logs = get_all_logs(logs_dir, job_filter, search_term if search_term else None, max_lines=10000)

    # Format for export
    export_lines = []
    for log in logs:
        export_lines.append(f"[{log['job_name']}] {log['line']}")

    export_content = "\n".join(export_lines)

    # Generate filename
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"backup_logs_{job_filter}_{timestamp}.txt"

    return Response(
        export_content,
        mimetype='text/plain',
        headers={'Content-Disposition': f'attachment; filename={filename}'}
    )
