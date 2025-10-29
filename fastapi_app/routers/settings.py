"""
Settings routes (FastAPI)
"""
from fastapi import APIRouter, Request, Form
from fastapi.responses import HTMLResponse
from core.settings import get_settings
from utils.rclone_helper import is_rclone_installed, get_rclone_version
import shutil

# Import FlaskCompatRequest, templates, and helpers from main app
from fastapi_app import FlaskCompatRequest, templates, create_flash_getter

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Settings page"""
    settings_obj = get_settings()
    settings = settings_obj.get_all()

    # Check tool installation
    rsync_installed = shutil.which('rsync') is not None
    rclone_installed, rclone_path = is_rclone_installed()
    rclone_version = get_rclone_version()

    # Get system paths
    from core.paths import get_jobs_file, get_settings_file, get_logs_dir
    system_info = {
        'jobs_file': str(get_jobs_file()),
        'settings_file': str(get_settings_file()),
        'logs_dir': str(get_logs_dir())
    }

    return templates.TemplateResponse('settings.html', {
        'request': FlaskCompatRequest(request),
        'settings': settings,
        'rsync_installed': rsync_installed,
        'rclone_installed': rclone_installed,
        'rclone_version': rclone_version,
        'rclone_path': rclone_path if rclone_installed else None,
        'system_info': system_info,
        'get_flashed_messages': create_flash_getter(request.session)
    })


@router.post("/save", response_class=HTMLResponse)
async def save(
    request: Request,
    default_bandwidth_limit: int = Form(0),
    auto_start_on_launch: str = Form(None),
    network_check_interval: int = Form(30),
    max_retry_attempts: int = Form(10),
    auto_refresh_interval: int = Form(2)
):
    """Save settings (HTMX endpoint)"""
    try:
        # Build settings dict
        new_settings = {
            'default_bandwidth_limit': default_bandwidth_limit,
            'auto_start_on_launch': auto_start_on_launch == 'on',
            'network_check_interval': network_check_interval,
            'max_retry_attempts': max_retry_attempts,
            'auto_refresh_interval': auto_refresh_interval
        }

        # Validate
        if new_settings['network_check_interval'] < 5:
            request.session['flash'] = {'message': 'Network check interval must be at least 5 seconds', 'category': 'error'}
            return templates.TemplateResponse('partials/flash_messages.html', {
                'request': FlaskCompatRequest(request),
                'get_flashed_messages': create_flash_getter(request.session)
            }, status_code=400)

        if new_settings['max_retry_attempts'] < 1:
            request.session['flash'] = {'message': 'Max retry attempts must be at least 1', 'category': 'error'}
            return templates.TemplateResponse('partials/flash_messages.html', {
                'request': FlaskCompatRequest(request),
                'get_flashed_messages': create_flash_getter(request.session)
            }, status_code=400)

        # Save settings using Settings class API
        settings_obj = get_settings()
        for key, value in new_settings.items():
            settings_obj.set(key, value)

        request.session['flash'] = {'message': 'Settings saved successfully!', 'category': 'success'}

        return templates.TemplateResponse('partials/flash_messages.html', {
            'request': FlaskCompatRequest(request),
            'get_flashed_messages': create_flash_getter(request.session)
        })

    except ValueError as e:
        request.session['flash'] = {'message': f'Invalid value: {str(e)}', 'category': 'error'}
        return templates.TemplateResponse('partials/flash_messages.html', {
            'request': FlaskCompatRequest(request),
            'get_flashed_messages': create_flash_getter(request.session)
        }, status_code=400)
    except Exception as e:
        request.session['flash'] = {'message': f'Error saving settings: {str(e)}', 'category': 'error'}
        return templates.TemplateResponse('partials/flash_messages.html', {
            'request': FlaskCompatRequest(request),
            'get_flashed_messages': create_flash_getter(request.session)
        }, status_code=500)


@router.post("/reset", response_class=HTMLResponse)
async def reset(request: Request):
    """Reset settings to defaults (HTMX endpoint)"""
    try:
        settings_obj = get_settings()
        settings_obj.reset_to_defaults()
        defaults = settings_obj.get_all()

        request.session['flash'] = {'message': 'Settings reset to defaults!', 'category': 'success'}

        # Return full settings form with new values
        return templates.TemplateResponse('partials/settings_form.html', {
            'request': FlaskCompatRequest(request),
            'settings': defaults,
            'get_flashed_messages': create_flash_getter(request.session)
        })

    except Exception as e:
        request.session['flash'] = {'message': f'Error resetting settings: {str(e)}', 'category': 'error'}
        return templates.TemplateResponse('partials/flash_messages.html', {
            'request': FlaskCompatRequest(request),
            'get_flashed_messages': create_flash_getter(request.session)
        }, status_code=500)
