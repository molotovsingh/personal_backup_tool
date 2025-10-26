"""
Dashboard routes
"""
from flask import Blueprint, render_template, session, flash, redirect, url_for
from services.dashboard_service import (
    get_dashboard_data,
    get_dashboard_stats,
    get_active_jobs,
    get_recent_activity,
    recover_interrupted_jobs
)
from core.job_manager import JobManager

dashboard_bp = Blueprint('dashboard', __name__)


@dashboard_bp.route('/')
def index():
    """Dashboard homepage"""
    # Get all dashboard data from service layer
    data = get_dashboard_data()
    stats = data['stats']

    return render_template('dashboard.html',
                           active_jobs_count=stats.active_jobs_count,
                           total_jobs_count=stats.total_jobs_count,
                           total_bytes=stats.total_bytes,
                           active_jobs=data['active_jobs'],
                           recent_jobs=data['recent_jobs'])


@dashboard_bp.route('/stats')
def stats():
    """Get dashboard stats (HTMX endpoint)"""
    # Get jobs and calculate stats via service layer
    manager = JobManager()
    jobs = manager.list_jobs()
    dashboard_stats = get_dashboard_stats(jobs)

    return render_template('partials/dashboard_stats.html',
                           active_jobs_count=dashboard_stats.active_jobs_count,
                           total_jobs_count=dashboard_stats.total_jobs_count,
                           total_bytes=dashboard_stats.total_bytes)


@dashboard_bp.route('/active-jobs')
def active_jobs_partial():
    """Get active jobs list (HTMX endpoint)"""
    manager = JobManager()
    jobs = manager.list_jobs()

    # Get active jobs via service layer
    active = get_active_jobs(jobs, limit=5)

    return render_template('partials/dashboard_active_jobs.html',
                           active_jobs=active)


@dashboard_bp.route('/recent-activity')
def recent_activity():
    """Get recent activity (HTMX endpoint)"""
    manager = JobManager()
    jobs = manager.list_jobs()

    # Get recent activity via service layer
    recent = get_recent_activity(jobs, limit=10)

    return render_template('partials/dashboard_recent_activity.html',
                           recent_jobs=recent)


@dashboard_bp.route('/recover-jobs', methods=['POST'])
def recover_jobs():
    """Recover interrupted jobs by marking them as paused"""
    try:
        interrupted_job_ids = session.get('interrupted_jobs', [])

        # Use service layer to handle recovery logic
        recovered_count, message = recover_interrupted_jobs(interrupted_job_ids)

        # Flash appropriate message
        if recovered_count > 0:
            flash(message, 'success')
        else:
            flash(message, 'info')

        # Clear recovery prompt
        session['show_recovery_prompt'] = False
        session.pop('interrupted_jobs', None)

    except Exception as e:
        flash(f'Error recovering jobs: {str(e)}', 'error')

    return redirect(url_for('dashboard.index'))


@dashboard_bp.route('/dismiss-recovery', methods=['POST'])
def dismiss_recovery():
    """Dismiss the crash recovery prompt"""
    session['show_recovery_prompt'] = False
    session.pop('interrupted_jobs', None)
    flash('Recovery prompt dismissed', 'info')
    return redirect(url_for('dashboard.index'))
