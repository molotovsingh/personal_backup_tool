"""
Flask application configuration
"""
import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).parent.parent


class Config:
    """Base configuration"""
    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'

    # Session settings
    SESSION_TYPE = 'filesystem'
    SESSION_FILE_DIR = os.path.join(BASE_DIR, 'flask_sessions')
    SESSION_PERMANENT = False
    SESSION_USE_SIGNER = True

    # SocketIO settings
    SOCKETIO_MESSAGE_QUEUE = None

    # Application settings
    JOBS_FILE = os.path.join(BASE_DIR, 'jobs.yaml')
    SETTINGS_FILE = os.path.join(BASE_DIR, 'settings.yaml')
    LOGS_DIR = os.path.join(BASE_DIR, 'logs')

    # Auto-refresh settings
    DEFAULT_REFRESH_INTERVAL = 2  # seconds


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    ENV = 'development'


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    ENV = 'production'
    # In production, SECRET_KEY must be set via environment variable
    SECRET_KEY = os.environ.get('SECRET_KEY') or Config.SECRET_KEY

    def __init__(self):
        # Validate SECRET_KEY only when actually using production config
        if not os.environ.get('SECRET_KEY'):
            import warnings
            warnings.warn('SECRET_KEY not set via environment variable in production mode')


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
