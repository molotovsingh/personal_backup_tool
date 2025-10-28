"""
Flask application configuration
"""
import os
from pathlib import Path
from core.paths import get_data_dir, get_jobs_file, get_settings_file, get_logs_dir

# Base directory (for Flask-specific assets only)
BASE_DIR = Path(__file__).parent.parent


class Config:
    """Base configuration"""
    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'

    # CSRF Protection
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None  # No timeout for long-running transfers

    # Session settings
    SESSION_TYPE = 'filesystem'
    SESSION_FILE_DIR = os.path.join(BASE_DIR, 'flask_sessions')
    SESSION_PERMANENT = False
    SESSION_USE_SIGNER = True
    SESSION_COOKIE_SECURE = False  # Will be True in production
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

    # CORS settings (default allows localhost and 127.0.0.1)
    CORS_ALLOWED_ORIGINS = os.environ.get('CORS_ALLOWED_ORIGINS', 'http://localhost:5001,http://127.0.0.1:5001,http://localhost:5002,http://127.0.0.1:5002').split(',')

    # SocketIO settings
    SOCKETIO_MESSAGE_QUEUE = None
    SOCKETIO_LOGGER = False  # Will be True only in development
    SOCKETIO_ENGINEIO_LOGGER = False  # Will be True only in development

    # Application settings (using centralized path management)
    JOBS_FILE = str(get_jobs_file())
    SETTINGS_FILE = str(get_settings_file())
    LOGS_DIR = str(get_logs_dir())
    DATA_DIR = str(get_data_dir())

    # Auto-refresh settings
    DEFAULT_REFRESH_INTERVAL = 2  # seconds


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    ENV = 'development'

    # Enable debug logging in development
    SOCKETIO_LOGGER = True
    SOCKETIO_ENGINEIO_LOGGER = True


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    ENV = 'production'

    # SECRET_KEY will be validated during app creation
    SECRET_KEY = os.environ.get('SECRET_KEY') or Config.SECRET_KEY

    # Secure session cookies (HTTPS only)
    SESSION_COOKIE_SECURE = True

    # Disable debug logging in production
    SOCKETIO_LOGGER = False
    SOCKETIO_ENGINEIO_LOGGER = False


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
