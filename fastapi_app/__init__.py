"""
FastAPI Backup Manager Application
"""
from fastapi import FastAPI, Request, WebSocket
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.cors import CORSMiddleware
import os
import asyncio

# Initialize FastAPI app
app = FastAPI(
    title="Backup Manager",
    description="Personal backup orchestration tool",
    version="2.0.0"
)

# Session middleware (replaces Flask-Session)
app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv("SECRET_KEY", "dev-secret-key-change-in-production"),
    session_cookie="backup_session"
)

# CORS middleware (replaces Flask-CORS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5000", "http://localhost:5001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Static files
app.mount("/static", StaticFiles(directory="fastapi_app/static"), name="static")

# Templates
templates = Jinja2Templates(directory="fastapi_app/templates")

# Add Flask compatibility functions to Jinja2 environment
def generate_csrf_token():
    """Generate a CSRF token (placeholder for FastAPI migration)"""
    import secrets
    return secrets.token_hex(16)

# Add to globals
templates.env.globals['csrf_token'] = generate_csrf_token

# Note: get_flashed_messages needs to be passed per-request via template context
# because it needs access to the session. It's implemented in router handlers.

# Helper function to create get_flashed_messages for templates
def create_flash_getter(session):
    """Create a get_flashed_messages function bound to a session"""
    def get_flashed_messages(with_categories=False):
        flash = session.pop('flash', None)
        if not flash:
            return []
        if with_categories:
            return [(flash.get('category', 'info'), flash.get('message', ''))]
        return [flash.get('message', '')]
    return get_flashed_messages

# Add custom request object wrapper for Flask compatibility
class FlaskCompatRequest:
    """Wrapper to make Starlette Request compatible with Flask templates"""
    def __init__(self, request: Request):
        self._request = request
        self.url = request.url
        self.path = request.url.path

    @property
    def endpoint(self):
        """Return endpoint name from path (Flask compatibility)"""
        # Extract endpoint from path, e.g., "/jobs" -> "jobs"
        path = self.path.strip('/')
        return path.split('/')[0] if path else 'dashboard'

    def __getattr__(self, name):
        """Forward other attributes to underlying request"""
        return getattr(self._request, name)

# Include routers
from fastapi_app.routers import dashboard, jobs, settings, logs
app.include_router(dashboard.router, tags=["dashboard"])
app.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
app.include_router(settings.router, prefix="/settings", tags=["settings"])
app.include_router(logs.router, prefix="/logs", tags=["logs"])

# Error handlers
from fastapi.exceptions import HTTPException
from starlette.exceptions import HTTPException as StarletteHTTPException

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions with custom error pages"""
    if exc.status_code == 404:
        return templates.TemplateResponse(
            "errors/404.html",
            {
                "request": FlaskCompatRequest(request),
                "get_flashed_messages": create_flash_getter(request.session)
            },
            status_code=404
        )
    elif exc.status_code == 500:
        import logging
        logging.error(f'Server Error: {exc}')
        return templates.TemplateResponse(
            "errors/500.html",
            {
                "request": FlaskCompatRequest(request),
                "get_flashed_messages": create_flash_getter(request.session)
            },
            status_code=500
        )
    # For other HTTP errors, return default FastAPI response
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail}
    )

# WebSocket endpoint
@app.websocket("/ws")
async def websocket_route(websocket: WebSocket):
    """WebSocket endpoint for real-time job updates"""
    from fastapi_app.background import websocket_endpoint
    await websocket_endpoint(websocket)


# Startup event: Start background monitoring task
@app.on_event("startup")
async def startup_event():
    """Start background tasks on app startup"""
    from fastapi_app.background import monitor_jobs_task, start_log_indexer
    from services.dashboard_service import recover_interrupted_jobs
    from services.job_service import get_jobs_list

    # Recover any jobs stuck in "running" state (zombie jobs from crashes/restarts)
    all_jobs = get_jobs_list()
    interrupted_job_ids = [j['id'] for j in all_jobs if j['status'] == 'running']
    if interrupted_job_ids:
        count, msg = recover_interrupted_jobs(interrupted_job_ids)
        import logging
        logging.info(f"Startup recovery: {msg}")

    asyncio.create_task(monitor_jobs_task())
    await start_log_indexer()
    import logging
    logging.info("FastAPI application started, background tasks initiated")


# Shutdown event: Stop background tasks
@app.on_event("shutdown")
async def shutdown_event():
    """Stop background tasks on app shutdown"""
    from fastapi_app.background import stop_log_indexer
    await stop_log_indexer()
    import logging
    logging.info("FastAPI application shutting down, background tasks stopped")


# Health check endpoint
@app.get("/health")
async def health_check():
    """
    Health check endpoint for monitoring

    Returns:
        JSON with system health status including:
        - Overall status (healthy/degraded/unhealthy)
        - Database connectivity
        - Background tasks status
        - Active jobs count
        - Engine count
        - Recent errors (if any)
    """
    import logging
    from datetime import datetime
    from core.job_manager import JobManager
    from pathlib import Path

    health_status = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "components": {}
    }

    # Check storage/database
    try:
        manager = JobManager()
        job_count = manager.storage.count_jobs()
        health_status["components"]["storage"] = {
            "status": "healthy",
            "job_count": job_count
        }
    except Exception as e:
        logging.error(f"Health check: Storage error - {e}")
        health_status["status"] = "degraded"
        health_status["components"]["storage"] = {
            "status": "unhealthy",
            "error": str(e)
        }

    # Check background tasks
    try:
        from fastapi_app.background import log_indexer
        log_indexer_status = "running" if log_indexer else "stopped"
        health_status["components"]["background_tasks"] = {
            "status": "healthy" if log_indexer else "degraded",
            "log_indexer": log_indexer_status
        }
    except Exception as e:
        logging.error(f"Health check: Background tasks error - {e}")
        health_status["status"] = "degraded"
        health_status["components"]["background_tasks"] = {
            "status": "unhealthy",
            "error": str(e)
        }

    # Check job engines
    try:
        manager = JobManager()
        with manager._engines_lock:
            engine_count = len(manager.engines)
            running_engines = sum(1 for e in manager.engines.values() if e.is_running())

        health_status["components"]["job_engines"] = {
            "status": "healthy",
            "total_engines": engine_count,
            "running_engines": running_engines
        }
    except Exception as e:
        logging.error(f"Health check: Job engines error - {e}")
        health_status["status"] = "degraded"
        health_status["components"]["job_engines"] = {
            "status": "unhealthy",
            "error": str(e)
        }

    # Check logs directory
    try:
        logs_path = Path.home() / "backup-manager" / "logs"
        logs_exist = logs_path.exists()
        health_status["components"]["logs"] = {
            "status": "healthy" if logs_exist else "degraded",
            "path_exists": logs_exist
        }
    except Exception as e:
        logging.error(f"Health check: Logs error - {e}")
        health_status["components"]["logs"] = {
            "status": "degraded",
            "error": str(e)
        }

    # Check error events statistics (Task 6.5)
    try:
        from core.error_repository import get_error_repository
        error_repo = get_error_repository()
        error_stats = error_repo.get_error_stats()

        # Determine health status based on unresolved errors
        unresolved = error_stats.get('unresolved', 0)
        recent_24h = error_stats.get('recent_24h', 0)
        critical_count = error_stats.get('by_severity', {}).get('CRITICAL', 0)

        if critical_count > 0:
            error_health_status = "degraded"
        elif unresolved > 10 or recent_24h > 20:
            error_health_status = "degraded"
        else:
            error_health_status = "healthy"

        health_status["components"]["error_tracking"] = {
            "status": error_health_status,
            "total_errors": error_stats.get('total', 0),
            "unresolved_errors": unresolved,
            "recent_24h": recent_24h,
            "critical_errors": critical_count
        }
    except Exception as e:
        logging.error(f"Health check: Error tracking error - {e}")
        health_status["components"]["error_tracking"] = {
            "status": "degraded",
            "error": str(e)
        }

    # Set overall status based on components
    if any(c.get("status") == "unhealthy" for c in health_status["components"].values()):
        health_status["status"] = "unhealthy"
    elif any(c.get("status") == "degraded" for c in health_status["components"].values()):
        health_status["status"] = "degraded"

    return health_status


# Test route to verify WebSocket connection
@app.get("/test", response_class=HTMLResponse)
async def test_page(request: Request):
    """Simple test page to verify WebSocket connection"""
    html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>FastAPI WebSocket Test</title>
    <style>
        body { font-family: Arial, sans-serif; padding: 20px; }
        #messages { border: 1px solid #ccc; padding: 10px; height: 300px; overflow-y: scroll; }
        .message { margin: 5px 0; padding: 5px; background: #f0f0f0; }
        .connected { color: green; }
        .disconnected { color: red; }
        .job-update { color: blue; }
    </style>
</head>
<body>
    <h1>FastAPI WebSocket Test</h1>
    <div id="status" class="disconnected">Disconnected</div>
    <div id="messages"></div>

    <script>
        const ws = new WebSocket('ws://localhost:5001/ws');
        const messagesDiv = document.getElementById('messages');
        const statusDiv = document.getElementById('status');

        ws.onopen = () => {
            statusDiv.textContent = 'Connected';
            statusDiv.className = 'connected';
            addMessage('WebSocket connected', 'connected');
        };

        ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            console.log('Received:', data);
            addMessage(JSON.stringify(data, null, 2), 'job-update');
        };

        ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            addMessage('WebSocket error: ' + error, 'disconnected');
        };

        ws.onclose = () => {
            statusDiv.textContent = 'Disconnected';
            statusDiv.className = 'disconnected';
            addMessage('WebSocket disconnected', 'disconnected');
        };

        function addMessage(text, className) {
            const msg = document.createElement('div');
            msg.className = 'message ' + className;
            msg.textContent = new Date().toLocaleTimeString() + ': ' + text;
            messagesDiv.appendChild(msg);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }
    </script>
</body>
</html>
    """
    from fastapi.responses import HTMLResponse
    return HTMLResponse(content=html_content)
