"""
Dashboard service layer

Handles all business logic for the dashboard page, including stats calculation,
job filtering, and recovery operations.
"""

from dataclasses import dataclass
from typing import List, Dict, Tuple
from core.job_manager import JobManager
from storage.job_storage import JobStorage


@dataclass
class DashboardStats:
    """Dashboard statistics data structure"""
    active_jobs_count: int
    total_jobs_count: int
    total_bytes: int
    total_bytes_formatted: str


def format_bytes(bytes_value: int) -> str:
    """
    Format bytes into human-readable string

    Args:
        bytes_value: Number of bytes

    Returns:
        Formatted string (e.g., "1.5 GB", "512 MB")
    """
    if bytes_value >= 1024**4:  # TB
        return f"{bytes_value / 1024**4:.2f} TB"
    elif bytes_value >= 1024**3:  # GB
        return f"{bytes_value / 1024**3:.2f} GB"
    elif bytes_value >= 1024**2:  # MB
        return f"{bytes_value / 1024**2:.2f} MB"
    elif bytes_value >= 1024:  # KB
        return f"{bytes_value / 1024:.2f} KB"
    else:
        return f"{bytes_value} B"


def get_dashboard_stats(jobs: List[Dict]) -> DashboardStats:
    """
    Calculate high-level dashboard statistics

    Args:
        jobs: List of job dictionaries from JobManager

    Returns:
        DashboardStats object with calculated statistics
    """
    active_jobs_count = sum(1 for job in jobs if job['status'] == 'running')
    total_jobs_count = len(jobs)
    total_bytes = sum(job.get('progress', {}).get('bytes_transferred', 0) for job in jobs)
    total_bytes_formatted = format_bytes(total_bytes)

    return DashboardStats(
        active_jobs_count=active_jobs_count,
        total_jobs_count=total_jobs_count,
        total_bytes=total_bytes,
        total_bytes_formatted=total_bytes_formatted
    )


def get_active_jobs(jobs: List[Dict], limit: int = 5) -> List[Dict]:
    """
    Filter and return active/running jobs

    Args:
        jobs: List of all jobs
        limit: Maximum number of jobs to return (default: 5)

    Returns:
        List of running jobs, limited to specified count
    """
    active = [job for job in jobs if job['status'] == 'running']
    return active[:limit]


def get_recent_activity(jobs: List[Dict], limit: int = 10) -> List[Dict]:
    """
    Get recently updated jobs sorted by update time

    Args:
        jobs: List of all jobs
        limit: Maximum number of jobs to return (default: 10)

    Returns:
        List of jobs sorted by most recent activity
    """
    sorted_jobs = sorted(jobs, key=lambda x: x.get('updated_at', ''), reverse=True)
    return sorted_jobs[:limit]


def get_dashboard_data() -> Dict:
    """
    Single entry point for dashboard to get all required data

    This function orchestrates all data retrieval and calculation needed
    by the dashboard page.

    Returns:
        Dictionary containing:
        - stats: DashboardStats object
        - active_jobs: List of running jobs (max 5)
        - recent_jobs: List of recently updated jobs (max 10)
        - all_jobs: Complete list of all jobs
    """
    manager = JobManager()
    jobs = manager.list_jobs()

    return {
        'stats': get_dashboard_stats(jobs),
        'active_jobs': get_active_jobs(jobs, limit=5),
        'recent_jobs': get_recent_activity(jobs, limit=10),
        'all_jobs': jobs
    }


def recover_interrupted_jobs(job_ids: List[str]) -> Tuple[int, str]:
    """
    Recover interrupted jobs by marking them as paused

    Args:
        job_ids: List of job IDs to recover

    Returns:
        Tuple of (recovered_count, message)
    """
    if not job_ids:
        return 0, 'No interrupted jobs to recover'

    storage = JobStorage()
    recovered_count = 0

    for job_id in job_ids:
        job = storage.get_job(job_id)
        if job and job.status == 'running':
            job.update_status('paused')
            storage.update_job(job)
            recovered_count += 1

    if recovered_count > 0:
        return recovered_count, f'Successfully recovered {recovered_count} interrupted job(s)'
    else:
        return 0, 'No jobs needed recovery'
