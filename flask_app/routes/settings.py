"""
Settings routes
"""
from flask import Blueprint, render_template, request, flash
from core.settings import get_settings
from utils.rclone_helper import is_rclone_installed, get_rclone_version
import shutil
import os

settings_bp = Blueprint('settings', __name__)


@settings_bp.route('/')
def index():
    """Settings page"""
    settings_obj = get_settings()
    settings = settings_obj.get_all()

    # Check tool installation
    rsync_installed = shutil.which('rsync') is not None
    rclone_installed, rclone_path = is_rclone_installed()
    rclone_version = get_rclone_version()

    # Get system paths
    from flask_app.config import Config
    system_info = {
        'jobs_file': Config.JOBS_FILE,
        'settings_file': Config.SETTINGS_FILE,
        'logs_dir': Config.LOGS_DIR
    }

    return render_template('settings.html',
                          settings=settings,
                          rsync_installed=rsync_installed,
                          rclone_installed=rclone_installed,
                          rclone_version=rclone_version,
                          rclone_path=rclone_path if rclone_installed else None,
                          system_info=system_info)


@settings_bp.route('/save', methods=['POST'])
def save():
    """Save settings (HTMX endpoint)"""
    try:
        # Get form data
        new_settings = {
            'default_bandwidth_limit': int(request.form.get('default_bandwidth_limit', 0)),
            'auto_start_on_launch': request.form.get('auto_start_on_launch') == 'on',
            'network_check_interval': int(request.form.get('network_check_interval', 30)),
            'max_retry_attempts': int(request.form.get('max_retry_attempts', 10)),
            'auto_refresh_interval': int(request.form.get('auto_refresh_interval', 2))
        }

        # Validate
        if new_settings['network_check_interval'] < 5:
            flash('Network check interval must be at least 5 seconds', 'error')
            return render_template('partials/flash_messages.html'), 400

        if new_settings['max_retry_attempts'] < 1:
            flash('Max retry attempts must be at least 1', 'error')
            return render_template('partials/flash_messages.html'), 400

        # Save settings using Settings class API
        settings_obj = get_settings()
        for key, value in new_settings.items():
            settings_obj.set(key, value)

        flash('Settings saved successfully!', 'success')

        return render_template('partials/flash_messages.html')

    except ValueError as e:
        flash(f'Invalid value: {str(e)}', 'error')
        return render_template('partials/flash_messages.html'), 400
    except Exception as e:
        flash(f'Error saving settings: {str(e)}', 'error')
        return render_template('partials/flash_messages.html'), 500


@settings_bp.route('/reset', methods=['POST'])
def reset():
    """Reset settings to defaults (HTMX endpoint)"""
    try:
        settings_obj = get_settings()
        settings_obj.reset_to_defaults()
        defaults = settings_obj.get_all()

        flash('Settings reset to defaults!', 'success')

        # Return full settings form with new values
        return render_template('partials/settings_form.html', settings=defaults)

    except Exception as e:
        flash(f'Error resetting settings: {str(e)}', 'error')
        return render_template('partials/flash_messages.html'), 500
