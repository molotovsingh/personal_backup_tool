"""
WebSocket event handlers for Flask-SocketIO
"""
import threading
import time
import atexit
from flask_socketio import emit, join_room, leave_room
from flask import request
from flask_app import socketio


# Background thread for polling job updates
background_thread = None
thread_stop_event = threading.Event()


@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print(f'Client connected: {request.sid}')
    emit('connection_response', {'status': 'connected'})

    # Start background thread if not already running
    global background_thread
    if background_thread is None:
        background_thread = socketio.start_background_task(job_update_background_thread)


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print(f'Client disconnected: {request.sid}')


@socketio.on('subscribe_to_job')
def handle_subscribe(data):
    """Subscribe client to job progress updates"""
    job_id = data.get('job_id')
    if job_id:
        join_room(f'job_{job_id}')
        emit('subscription_confirmed', {'job_id': job_id})


@socketio.on('unsubscribe_from_job')
def handle_unsubscribe(data):
    """Unsubscribe client from job progress updates"""
    job_id = data.get('job_id')
    if job_id:
        leave_room(f'job_{job_id}')
        emit('unsubscription_confirmed', {'job_id': job_id})


def job_update_background_thread():
    """Background thread that polls job status and emits updates"""
    from core.job_manager import JobManager

    print('Job update background thread started')

    while not thread_stop_event.is_set():
        try:
            manager = JobManager()
            jobs = manager.list_jobs()

            # Emit updates for running jobs
            for job in jobs:
                if job['status'] == 'running':
                    # Emit job update event (matching JavaScript listener)
                    socketio.emit('job_update', {
                        'job_id': job['id'],
                        'status': job['status'],
                        'percent': job['progress'].get('percent', 0),
                        'bytes_transferred': job['progress'].get('bytes_transferred', 0),
                        'total_bytes': job['progress'].get('total_bytes', 0),
                        'speed_bytes': job['progress'].get('speed_bytes', 0),
                        'eta_seconds': job['progress'].get('eta_seconds', 0),
                        'deletion': job['progress'].get('deletion', {})
                    })

        except Exception as e:
            print(f'Error in job update thread: {e}')

        # Sleep for 1 second between updates
        time.sleep(1)

    print('Job update background thread stopped')


def cleanup_background_thread():
    """Gracefully stop background thread on app shutdown"""
    global background_thread
    if background_thread:
        print('Stopping background thread...')
        thread_stop_event.set()
        # Give thread time to finish cleanly
        time.sleep(1.5)
        background_thread = None
        print('Background thread stopped')


# Register cleanup function to run on app shutdown
atexit.register(cleanup_background_thread)
