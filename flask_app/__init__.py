"""
Flask Backup Manager Application
"""
from flask import Flask, render_template, request
from flask_session import Session
from flask_socketio import SocketIO
import os
from pathlib import Path

# Initialize SocketIO (will be configured in create_app)
socketio = SocketIO()


def create_app(config_name='development'):
    """Application factory pattern"""
    app = Flask(__name__)

    # Load configuration
    from flask_app.config import config
    app.config.from_object(config[config_name])

    # Ensure required directories exist
    session_dir = Path(app.config['SESSION_FILE_DIR'])
    session_dir.mkdir(parents=True, exist_ok=True)

    # Initialize extensions
    Session(app)
    socketio.init_app(app,
                      cors_allowed_origins="*",
                      async_mode='threading',
                      logger=True,
                      engineio_logger=True)

    # Register blueprints
    from flask_app.routes.dashboard import dashboard_bp
    from flask_app.routes.jobs import jobs_bp
    from flask_app.routes.settings import settings_bp
    from flask_app.routes.logs import logs_bp

    app.register_blueprint(dashboard_bp)
    app.register_blueprint(jobs_bp, url_prefix='/jobs')
    app.register_blueprint(settings_bp, url_prefix='/settings')
    app.register_blueprint(logs_bp, url_prefix='/logs')

    # Register error handlers
    @app.errorhandler(404)
    def not_found(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        app.logger.error(f'Server Error: {error}')
        return render_template('errors/500.html'), 500

    # Register WebSocket handlers
    from flask_app import socketio_handlers

    # Context processor for crash recovery
    @app.context_processor
    def inject_crash_recovery():
        """Make interrupted jobs available to all templates"""
        from flask import session
        from core.job_manager import JobManager

        # Check if we've already checked for crashes in this session
        if 'crash_check_done' not in session:
            # Find interrupted jobs (status=running on app start)
            try:
                manager = JobManager()
                jobs = manager.list_jobs()
                interrupted = [j for j in jobs if j['status'] == 'running']

                if interrupted:
                    session['interrupted_jobs'] = [j['id'] for j in interrupted]
                    session['show_recovery_prompt'] = True
                else:
                    session['show_recovery_prompt'] = False

                session['crash_check_done'] = True
            except Exception as e:
                app.logger.error(f'Error checking for interrupted jobs: {e}')
                session['show_recovery_prompt'] = False
                session['crash_check_done'] = True

        return {
            'show_recovery_prompt': session.get('show_recovery_prompt', False),
            'interrupted_job_count': len(session.get('interrupted_jobs', []))
        }

    # Request logging
    @app.after_request
    def after_request(response):
        app.logger.info(f'{request.method} {request.path} - {response.status_code}')
        return response

    return app
