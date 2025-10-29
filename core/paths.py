"""
Central path management for Backup Manager

Provides a single source of truth for data directory location,
ensuring Flask and core modules use the same paths.
"""
import os
from pathlib import Path


def get_data_dir() -> Path:
    """
    Get the application data directory.

    The data directory location is determined by (in order of precedence):
    1. BACKUP_MANAGER_DATA_DIR environment variable
    2. Default: ~/backup-manager

    Returns:
        Path object pointing to the data directory
    """
    data_dir_env = os.environ.get('BACKUP_MANAGER_DATA_DIR')

    if data_dir_env:
        data_dir = Path(data_dir_env).expanduser().resolve()
    else:
        data_dir = Path.home() / 'backup-manager'

    # Ensure directory exists
    data_dir.mkdir(parents=True, exist_ok=True)

    return data_dir


def get_jobs_file() -> Path:
    """Get path to jobs.yaml file"""
    return get_data_dir() / 'jobs.yaml'


def get_settings_file() -> Path:
    """Get path to settings.yaml file"""
    return get_data_dir() / 'settings.yaml'


def get_logs_dir() -> Path:
    """
    Get path to logs directory

    Creates the directory if it doesn't exist.
    """
    logs_dir = get_data_dir() / 'logs'
    logs_dir.mkdir(parents=True, exist_ok=True)
    return logs_dir


def get_db_path() -> Path:
    """
    Get path to SQLite database file

    Creates the data directory if it doesn't exist.
    """
    data_dir = get_data_dir() / 'data'
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / 'logs.db'
