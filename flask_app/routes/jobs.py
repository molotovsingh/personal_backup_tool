"""
Jobs routes
"""
from flask import Blueprint, render_template, request, flash
from services.job_service import (
    get_jobs_list,
    create_job_from_form,
    start_job_operation,
    pause_job_operation,
    delete_job_operation
)

jobs_bp = Blueprint('jobs', __name__)


@jobs_bp.route('/')
def list_jobs():
    """List all jobs"""
    # Get jobs from service layer
    jobs = get_jobs_list()

    # If HTMX request, return partial
    if request.headers.get('HX-Request'):
        return render_template('partials/jobs_list.html', jobs=jobs)

    return render_template('jobs.html', jobs=jobs)


@jobs_bp.route('/create', methods=['POST'])
def create_job():
    """Create a new backup job"""
    try:
        # Extract form data as dictionary
        form_data = {
            'name': request.form.get('name', ''),
            'source': request.form.get('source', ''),
            'dest': request.form.get('dest', ''),
            'type': request.form.get('type', 'rsync'),
            'bandwidth_limit': request.form.get('bandwidth_limit', 0)
        }

        # Use service layer to validate and create job
        success, message, job = create_job_from_form(form_data)

        # Flash appropriate message
        if success:
            flash(message, 'success')
        else:
            flash(message, 'error')

        # Return updated job list with flash messages
        jobs = get_jobs_list()
        return render_template('partials/jobs_content.html', jobs=jobs)

    except ValueError as e:
        flash(f'Invalid input: {str(e)}', 'error')
        jobs = get_jobs_list()
        return render_template('partials/jobs_content.html', jobs=jobs), 400
    except Exception as e:
        flash(f'Error creating job: {str(e)}', 'error')
        jobs = get_jobs_list()
        return render_template('partials/jobs_content.html', jobs=jobs), 500


@jobs_bp.route('/<job_id>/start', methods=['POST'])
def start_job(job_id):
    """Start a backup job"""
    try:
        # Use service layer to start job
        success, message = start_job_operation(job_id)

        if success:
            flash(message, 'success')
        else:
            flash(message, 'error')

        # Return updated job list with flash messages
        jobs = get_jobs_list()
        return render_template('partials/jobs_content.html', jobs=jobs)

    except Exception as e:
        flash(f'Error starting job: {str(e)}', 'error')
        jobs = get_jobs_list()
        return render_template('partials/jobs_content.html', jobs=jobs), 500


@jobs_bp.route('/<job_id>/pause', methods=['POST'])
def pause_job(job_id):
    """Pause a running backup job"""
    try:
        # Use service layer to pause job
        success, message = pause_job_operation(job_id)

        if success:
            flash(message, 'success')
        else:
            flash(message, 'error')

        # Return updated job list with flash messages
        jobs = get_jobs_list()
        return render_template('partials/jobs_content.html', jobs=jobs)

    except Exception as e:
        flash(f'Error pausing job: {str(e)}', 'error')
        jobs = get_jobs_list()
        return render_template('partials/jobs_content.html', jobs=jobs), 500


@jobs_bp.route('/<job_id>/delete', methods=['DELETE'])
def delete_job(job_id):
    """Delete a backup job"""
    try:
        # Use service layer to delete job
        success, message = delete_job_operation(job_id)

        if success:
            flash(message, 'success')
        else:
            flash(message, 'error')

        # Return updated job list with flash messages
        jobs = get_jobs_list()
        return render_template('partials/jobs_content.html', jobs=jobs)

    except Exception as e:
        flash(f'Error deleting job: {str(e)}', 'error')
        jobs = get_jobs_list()
        return render_template('partials/jobs_content.html', jobs=jobs), 500
