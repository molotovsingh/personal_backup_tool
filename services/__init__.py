"""
Service layer for business logic

This package contains service modules that handle business logic,
keeping it decoupled from the presentation layer (Flask routes, Streamlit pages).
"""

from .dashboard_service import (
    get_dashboard_data,
    get_dashboard_stats,
    get_active_jobs,
    get_recent_activity,
    recover_interrupted_jobs
)

from .job_service import (
    get_jobs_list,
    create_job_from_form,
    start_job_operation,
    pause_job_operation,
    delete_job_operation
)

__all__ = [
    # Dashboard services
    'get_dashboard_data',
    'get_dashboard_stats',
    'get_active_jobs',
    'get_recent_activity',
    'recover_interrupted_jobs',

    # Job services
    'get_jobs_list',
    'create_job_from_form',
    'start_job_operation',
    'pause_job_operation',
    'delete_job_operation',
]
