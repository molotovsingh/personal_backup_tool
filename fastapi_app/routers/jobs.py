"""
Jobs routes (FastAPI)
"""
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse
from typing import Optional
from services.job_service import (
    get_jobs_list,
    create_job_from_form,
    start_job_operation,
    pause_job_operation,
    delete_job_operation
)

# Import FlaskCompatRequest, templates, and helpers from main app
from fastapi_app import FlaskCompatRequest, templates, create_flash_getter

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def list_jobs(request: Request):
    """List running jobs only"""
    # Get jobs from service layer and filter for running jobs
    all_jobs = get_jobs_list()
    jobs = [j for j in all_jobs if j['status'] == 'running']

    # If HTMX request, return partial
    if request.headers.get('HX-Request'):
        return templates.TemplateResponse('partials/jobs_list.html', {
            'request': FlaskCompatRequest(request),
            'jobs': jobs,
            'get_flashed_messages': create_flash_getter(request.session)
        })

    return templates.TemplateResponse('jobs.html', {
        'request': FlaskCompatRequest(request),
        'jobs': jobs,
        'get_flashed_messages': create_flash_getter(request.session)
    })


@router.get("/{job_id}/card", response_class=HTMLResponse)
async def get_job_card(job_id: str, request: Request):
    """Get a single job card HTML (for selective updates)"""
    # Get the specific job
    all_jobs = get_jobs_list()
    job = next((j for j in all_jobs if j['id'] == job_id), None)
    
    if not job:
        return HTMLResponse(content="", status_code=404)
    
    # Return just the job card HTML
    return templates.TemplateResponse('partials/job_card.html', {
        'request': FlaskCompatRequest(request),
        'job': job,
        'get_flashed_messages': create_flash_getter(request.session)
    })


@router.get("/{job_id}/details", response_class=HTMLResponse)
async def get_job_details(job_id: str, request: Request):
    """Get job details HTML (for lazy loading)"""
    # Get the specific job with full details
    all_jobs = get_jobs_list()
    job = next((j for j in all_jobs if j['id'] == job_id), None)
    
    if not job:
        return HTMLResponse(content="<div class='text-red-500'>Job not found</div>", status_code=404)
    
    # Return just the job details HTML
    return templates.TemplateResponse('partials/job_details.html', {
        'request': FlaskCompatRequest(request),
        'job': job,
        'get_flashed_messages': create_flash_getter(request.session)
    })


@router.get("/history", response_class=HTMLResponse)
async def job_history(request: Request):
    """List historical jobs (completed, failed, paused)"""
    # Get jobs from service layer and filter for non-running jobs
    all_jobs = get_jobs_list()
    jobs = [j for j in all_jobs if j['status'] != 'running']

    return templates.TemplateResponse('jobs_history.html', {
        'request': FlaskCompatRequest(request),
        'jobs': jobs,
        'get_flashed_messages': create_flash_getter(request.session)
    })


@router.get("/deletion-ui", response_class=HTMLResponse)
async def deletion_ui(request: Request, delete_source_after: str = 'false'):
    """Return deletion options UI partial (HTMX endpoint)"""
    # Check if deletion is enabled (checkbox state)
    show_options = delete_source_after == 'true'

    # Create response with deletion options partial
    response = templates.TemplateResponse('partials/deletion_options.html', {
        'request': FlaskCompatRequest(request),
        'show_options': show_options
    })

    # Add HTMX headers to prevent flash message interference and ensure clean swap
    response.headers['HX-Retarget'] = '#deletion-options'
    response.headers['HX-Reswap'] = 'innerHTML'

    return response


@router.post("/create", response_class=HTMLResponse)
async def create_job(
    request: Request,
    name: str = Form(...),
    source: str = Form(...),
    dest: str = Form(...),
    type: str = Form('rsync'),
    bandwidth_limit: int = Form(0),
    delete_source_after: Optional[str] = Form(None),
    deletion_mode: str = Form('verify_then_delete'),
    deletion_confirmed: Optional[str] = Form(None)
):
    """Create a new backup job"""
    try:
        # Extract form data as dictionary
        form_data = {
            'name': name,
            'source': source,
            'dest': dest,
            'type': type,
            'bandwidth_limit': bandwidth_limit,
            'delete_source_after': delete_source_after == 'true',
            'deletion_mode': deletion_mode,
            'deletion_confirmed': deletion_confirmed == 'true'
        }

        # Use service layer to validate and create job
        success, message, job = create_job_from_form(form_data)

        # Flash appropriate message
        if success:
            request.session['flash'] = {'message': message, 'category': 'success'}
        else:
            request.session['flash'] = {'message': message, 'category': 'error'}

        # Return updated job list with flash messages (filter for running jobs)
        all_jobs = get_jobs_list()
        jobs = [j for j in all_jobs if j['status'] == 'running']
        return templates.TemplateResponse('partials/jobs_content.html', {
            'request': FlaskCompatRequest(request),
            'jobs': jobs,
            'get_flashed_messages': create_flash_getter(request.session)
        })

    except ValueError as e:
        request.session['flash'] = {'message': f'Invalid input: {str(e)}', 'category': 'error'}
        all_jobs = get_jobs_list()
        jobs = [j for j in all_jobs if j['status'] == 'running']
        return templates.TemplateResponse('partials/jobs_content.html', {
            'request': FlaskCompatRequest(request),
            'jobs': jobs,
            'get_flashed_messages': create_flash_getter(request.session)
        }, status_code=400)
    except Exception as e:
        request.session['flash'] = {'message': f'Error creating job: {str(e)}', 'category': 'error'}
        all_jobs = get_jobs_list()
        jobs = [j for j in all_jobs if j['status'] == 'running']
        return templates.TemplateResponse('partials/jobs_content.html', {
            'request': FlaskCompatRequest(request),
            'jobs': jobs,
            'get_flashed_messages': create_flash_getter(request.session)
        }, status_code=500)


@router.post("/{job_id}/start", response_class=HTMLResponse)
async def start_job(request: Request, job_id: str):
    """Start a backup job"""
    try:
        # Use service layer to start job
        success, message = start_job_operation(job_id)

        if success:
            request.session['flash'] = {'message': message, 'category': 'success'}
        else:
            request.session['flash'] = {'message': message, 'category': 'error'}

        # Check if this is a selective update request (hx-target is the specific job card)
        hx_target = request.headers.get('HX-Target', '')
        if hx_target and 'data-job-id' in hx_target:
            # Return just the updated job card for selective update
            all_jobs = get_jobs_list()
            job = next((j for j in all_jobs if j['id'] == job_id), None)
            if job:
                return templates.TemplateResponse('partials/job_card.html', {
                    'request': FlaskCompatRequest(request),
                    'job': job,
                    'get_flashed_messages': create_flash_getter(request.session)
                })

        # Return updated job list with flash messages (filter for running jobs)
        all_jobs = get_jobs_list()
        jobs = [j for j in all_jobs if j['status'] == 'running']
        return templates.TemplateResponse('partials/jobs_content.html', {
            'request': FlaskCompatRequest(request),
            'jobs': jobs,
            'get_flashed_messages': create_flash_getter(request.session)
        })

    except Exception as e:
        request.session['flash'] = {'message': f'Error starting job: {str(e)}', 'category': 'error'}
        all_jobs = get_jobs_list()
        jobs = [j for j in all_jobs if j['status'] == 'running']
        return templates.TemplateResponse('partials/jobs_content.html', {
            'request': FlaskCompatRequest(request),
            'jobs': jobs,
            'get_flashed_messages': create_flash_getter(request.session)
        }, status_code=500)


@router.post("/{job_id}/pause", response_class=HTMLResponse)
async def pause_job(request: Request, job_id: str):
    """Pause a running backup job"""
    try:
        # Use service layer to pause job
        success, message = pause_job_operation(job_id)

        if success:
            request.session['flash'] = {'message': message, 'category': 'success'}
        else:
            request.session['flash'] = {'message': message, 'category': 'error'}

        # Check if this is a selective update request (hx-target is the specific job card)
        hx_target = request.headers.get('HX-Target', '')
        if hx_target and 'data-job-id' in hx_target:
            # Return just the updated job card for selective update
            all_jobs = get_jobs_list()
            job = next((j for j in all_jobs if j['id'] == job_id), None)
            if job:
                return templates.TemplateResponse('partials/job_card.html', {
                    'request': FlaskCompatRequest(request),
                    'job': job,
                    'get_flashed_messages': create_flash_getter(request.session)
                })

        # Return updated job list with flash messages (filter for running jobs)
        all_jobs = get_jobs_list()
        jobs = [j for j in all_jobs if j['status'] == 'running']
        return templates.TemplateResponse('partials/jobs_content.html', {
            'request': FlaskCompatRequest(request),
            'jobs': jobs,
            'get_flashed_messages': create_flash_getter(request.session)
        })

    except Exception as e:
        request.session['flash'] = {'message': f'Error pausing job: {str(e)}', 'category': 'error'}
        all_jobs = get_jobs_list()
        jobs = [j for j in all_jobs if j['status'] == 'running']
        return templates.TemplateResponse('partials/jobs_content.html', {
            'request': FlaskCompatRequest(request),
            'jobs': jobs,
            'get_flashed_messages': create_flash_getter(request.session)
        }, status_code=500)


@router.delete("/{job_id}/delete", response_class=HTMLResponse)
async def delete_job(request: Request, job_id: str):
    """Delete a backup job"""
    try:
        # Use service layer to delete job
        success, message = delete_job_operation(job_id)

        if success:
            # Note: WebSocket tracking cleanup not needed with native WebSocket
            # (no per-job tracking like Flask-SocketIO had)
            request.session['flash'] = {'message': message, 'category': 'success'}
        else:
            request.session['flash'] = {'message': message, 'category': 'error'}

        # Check if this is a selective update request (for deletion, return empty to remove the card)
        hx_target = request.headers.get('HX-Target', '')
        if hx_target and 'data-job-id' in hx_target:
            # Return empty content to remove the deleted job card
            return HTMLResponse(content="", status_code=200 if success else 404)

        # Return updated job list with flash messages (filter for running jobs)
        all_jobs = get_jobs_list()
        jobs = [j for j in all_jobs if j['status'] == 'running']
        return templates.TemplateResponse('partials/jobs_content.html', {
            'request': FlaskCompatRequest(request),
            'jobs': jobs,
            'get_flashed_messages': create_flash_getter(request.session)
        })

    except Exception as e:
        request.session['flash'] = {'message': f'Error deleting job: {str(e)}', 'category': 'error'}
        all_jobs = get_jobs_list()
        jobs = [j for j in all_jobs if j['status'] == 'running']
        return templates.TemplateResponse('partials/jobs_content.html', {
            'request': FlaskCompatRequest(request),
            'jobs': jobs,
            'get_flashed_messages': create_flash_getter(request.session)
        }, status_code=500)
