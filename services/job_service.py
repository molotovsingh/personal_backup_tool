"""
Job service layer

Handles all business logic for job operations including validation,
creation, and job lifecycle management.
"""

from typing import Dict, List, Tuple, Optional
from core.job_manager import JobManager


class JobFormData:
    """Data structure for validated job form data"""

    def __init__(self, name: str, source: str, dest: str, job_type: str, settings: Dict):
        self.name = name
        self.source = source
        self.dest = dest
        self.job_type = job_type
        self.settings = settings


def validate_form_input(form_data: Dict) -> Tuple[bool, Optional[str], Optional[JobFormData]]:
    """
    Validate and sanitize job form input

    Args:
        form_data: Dictionary of form fields from request

    Returns:
        Tuple of (is_valid, error_message, job_form_data)
        - is_valid: True if validation passed
        - error_message: Error message if validation failed, None otherwise
        - job_form_data: JobFormData object if valid, None otherwise
    """
    # Extract and sanitize fields
    name = form_data.get('name', '').strip()
    source = form_data.get('source', '').strip()
    dest = form_data.get('dest', '').strip()
    job_type = form_data.get('type', 'rsync').strip()
    bandwidth_limit = form_data.get('bandwidth_limit', 0)

    # Extract deletion settings
    delete_source_after = form_data.get('delete_source_after', False)
    deletion_mode = form_data.get('deletion_mode', 'verify_then_delete')
    deletion_confirmed = form_data.get('deletion_confirmed', False)

    # Validate required fields
    if not name:
        return False, 'Job name is required', None

    if not source:
        return False, 'Source path is required', None

    if not dest:
        return False, 'Destination path is required', None

    # Validate bandwidth limit
    try:
        bandwidth_limit = int(bandwidth_limit)
        if bandwidth_limit < 0:
            return False, 'Bandwidth limit must be non-negative', None
    except (ValueError, TypeError):
        return False, 'Invalid bandwidth limit value', None

    # Validate deletion settings
    if delete_source_after:
        if not deletion_confirmed:
            return False, 'You must confirm the deletion risks to enable source deletion', None

        if deletion_mode not in ['verify_then_delete', 'per_file']:
            return False, 'Invalid deletion mode selected', None

    # Construct job settings
    settings = {}
    if bandwidth_limit > 0:
        settings['bandwidth_limit'] = bandwidth_limit

    # Add deletion settings
    if delete_source_after:
        settings['delete_source_after'] = True
        settings['deletion_mode'] = deletion_mode
        settings['deletion_confirmed'] = deletion_confirmed
    else:
        settings['delete_source_after'] = False
        settings['deletion_mode'] = 'verify_then_delete'
        settings['deletion_confirmed'] = False

    job_data = JobFormData(
        name=name,
        source=source,
        dest=dest,
        job_type=job_type,
        settings=settings
    )

    return True, None, job_data


def get_jobs_list() -> List[Dict]:
    """
    Retrieve list of all jobs

    Returns:
        List of job dictionaries
    """
    manager = JobManager()
    return manager.list_jobs()


def create_job_from_form(form_data: Dict) -> Tuple[bool, str, Optional[Dict]]:
    """
    Create a new backup job from form data

    This function handles validation, sanitization, and job creation
    orchestration.

    Args:
        form_data: Dictionary of form fields from request

    Returns:
        Tuple of (success, message, job)
        - success: True if job was created successfully
        - message: Success or error message
        - job: Job dictionary if successful, None otherwise
    """
    # Validate form input
    is_valid, error_msg, job_data = validate_form_input(form_data)

    if not is_valid:
        return False, error_msg, None

    # Create job via JobManager
    manager = JobManager()
    success, message, job = manager.create_job(
        name=job_data.name,
        source=job_data.source,
        dest=job_data.dest,
        job_type=job_data.job_type,
        settings=job_data.settings
    )

    if success:
        return True, f'Job "{job_data.name}" created successfully!', job
    else:
        return False, f'Failed to create job: {message}', None


def start_job_operation(job_id: str) -> Tuple[bool, str]:
    """
    Start a backup job

    Args:
        job_id: ID of the job to start

    Returns:
        Tuple of (success, message)
    """
    manager = JobManager()
    return manager.start_job(job_id)


def pause_job_operation(job_id: str) -> Tuple[bool, str]:
    """
    Pause a running backup job

    Args:
        job_id: ID of the job to pause

    Returns:
        Tuple of (success, message)
    """
    manager = JobManager()
    success, message = manager.stop_job(job_id)

    if success:
        return True, 'Job paused successfully'
    else:
        return False, f'Failed to pause job: {message}'


def delete_job_operation(job_id: str) -> Tuple[bool, str]:
    """
    Delete a backup job

    Args:
        job_id: ID of the job to delete

    Returns:
        Tuple of (success, message)
    """
    manager = JobManager()
    success, message = manager.delete_job(job_id)

    if success:
        return True, 'Job deleted successfully'
    else:
        return False, f'Failed to delete job: {message}'
