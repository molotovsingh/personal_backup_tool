"""
Dashboard routes (FastAPI)
"""
from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from services.dashboard_service import (
    get_dashboard_data,
    get_dashboard_stats,
    get_active_jobs,
    get_recent_activity,
    recover_interrupted_jobs
)
from core.job_manager import JobManager

# Import FlaskCompatRequest, templates, and helpers from main app
from fastapi_app import FlaskCompatRequest, templates, create_flash_getter

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Dashboard homepage"""
    # Get all dashboard data from service layer
    data = get_dashboard_data()
    stats = data['stats']

    # Check for crash recovery prompt
    show_recovery_prompt = request.session.get('show_recovery_prompt', False)
    interrupted_job_count = len(request.session.get('interrupted_jobs', []))

    return templates.TemplateResponse('dashboard.html', {
        'request': FlaskCompatRequest(request),
        'active_jobs_count': stats.active_jobs_count,
        'total_jobs_count': stats.total_jobs_count,
        'total_bytes': stats.total_bytes,
        'active_jobs': data['active_jobs'],
        'recent_jobs': data['recent_jobs'],
        'show_recovery_prompt': show_recovery_prompt,
        'interrupted_job_count': interrupted_job_count,
        'get_flashed_messages': create_flash_getter(request.session)
    })


@router.get("/stats", response_class=HTMLResponse)
async def stats(request: Request):
    """Get dashboard stats (HTMX endpoint)"""
    # Get jobs and calculate stats via service layer
    manager = JobManager()
    jobs = manager.list_jobs()
    dashboard_stats = get_dashboard_stats(jobs)

    return templates.TemplateResponse('partials/dashboard_stats.html', {
        'request': FlaskCompatRequest(request),
        'active_jobs_count': dashboard_stats.active_jobs_count,
        'total_jobs_count': dashboard_stats.total_jobs_count,
        'total_bytes': dashboard_stats.total_bytes
    })


@router.get("/active-jobs", response_class=HTMLResponse)
async def active_jobs_partial(request: Request):
    """Get active jobs list (HTMX endpoint)"""
    manager = JobManager()
    jobs = manager.list_jobs()

    # Get active jobs via service layer
    active = get_active_jobs(jobs, limit=5)

    return templates.TemplateResponse('partials/dashboard_active_jobs.html', {
        'request': FlaskCompatRequest(request),
        'active_jobs': active
    })


@router.get("/recent-activity", response_class=HTMLResponse)
async def recent_activity(request: Request):
    """Get recent activity (HTMX endpoint)"""
    manager = JobManager()
    jobs = manager.list_jobs()

    # Get recent activity via service layer
    recent = get_recent_activity(jobs, limit=10)

    return templates.TemplateResponse('partials/dashboard_recent_activity.html', {
        'request': FlaskCompatRequest(request),
        'recent_jobs': recent
    })


@router.post("/recover-jobs")
async def recover_jobs(request: Request):
    """Recover interrupted jobs by marking them as paused"""
    try:
        interrupted_job_ids = request.session.get('interrupted_jobs', [])

        # Use service layer to handle recovery logic
        recovered_count, message = recover_interrupted_jobs(interrupted_job_ids)

        # Flash appropriate message
        if recovered_count > 0:
            request.session['flash'] = {'message': message, 'category': 'success'}
        else:
            request.session['flash'] = {'message': message, 'category': 'info'}

        # Clear recovery prompt
        request.session['show_recovery_prompt'] = False
        request.session.pop('interrupted_jobs', None)

    except Exception as e:
        request.session['flash'] = {'message': f'Error recovering jobs: {str(e)}', 'category': 'error'}

    return RedirectResponse(url='/', status_code=303)


@router.post("/dismiss-recovery")
async def dismiss_recovery(request: Request):
    """Dismiss the crash recovery prompt"""
    request.session['show_recovery_prompt'] = False
    request.session.pop('interrupted_jobs', None)
    request.session['flash'] = {'message': 'Recovery prompt dismissed', 'category': 'info'}
    return RedirectResponse(url='/', status_code=303)
