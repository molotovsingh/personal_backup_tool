"""
Background Tasks
Async background tasks for job monitoring and WebSocket updates
"""
from fastapi import WebSocket, WebSocketDisconnect
from fastapi_app.websocket.manager import manager
from core.job_manager import JobManager
from core.log_indexer import LogIndexer
from core.error_repository import get_error_repository
from models.error_event import ErrorEvent
import asyncio

# Global log indexer instance
log_indexer = None


async def monitor_jobs_task():
    """
    Background task to monitor running jobs and broadcast updates via WebSocket.
    Runs continuously, checking job status every second.
    Sends final update when job transitions from running to completed/failed/paused.
    Also updates job state from engines and performs periodic cleanup.
    """
    import logging
    logging.info("Background job monitoring task started")

    # Track previous job states to detect transitions
    previous_states = {}
    cleanup_counter = 0  # Run cleanup every 10 seconds

    while True:
        try:
            job_manager = JobManager()

            # Get job list to check for running jobs
            jobs = job_manager.list_jobs()
            running_jobs = [job for job in jobs if job['status'] == 'running']
            has_running_jobs = len(running_jobs) > 0

            # Only process jobs if there are running jobs
            if has_running_jobs:
                # Update running jobs from their engines
                for job in running_jobs:
                    # Update job state from engine (handles progress saving)
                    job_manager.update_job_from_engine(job['id'])

                # Periodic engine cleanup (every 10 seconds when jobs are running)
                cleanup_counter += 1
                if cleanup_counter >= 10:
                    cleaned = job_manager.cleanup_stopped_engines()
                    if cleaned > 0:
                        logging.info(f"Cleaned up {cleaned} stopped engine(s)")
                    cleanup_counter = 0

                # Get fresh job list after updates
                jobs = job_manager.list_jobs()

                # Batch updates for all jobs (Task 7.3 - max 10 batches/second)
                # Since we sleep for 1 second, we send at most 1 batch/second
                updates_batch = []

                for job in jobs:
                    job_id = job['id']
                    current_status = job['status']
                    previous_status = previous_states.get(job_id)

                    # Collect running job updates
                    if current_status == 'running':
                        updates_batch.append({
                            'type': 'job_update',
                            'job_id': job_id,
                            'status': current_status,
                            'percent': job['progress'].get('percent', 0),
                            'bytes_transferred': job['progress'].get('bytes_transferred', 0),
                            'total_bytes': job['progress'].get('total_bytes', 0),
                            'speed_bytes': job['progress'].get('speed_bytes', 0),
                            'eta_seconds': job['progress'].get('eta_seconds', 0),
                            'deletion': job['progress'].get('deletion', {})
                        })

                    # Collect final updates when job finishes (transitions from running)
                    elif previous_status == 'running' and current_status in ['completed', 'failed', 'paused']:
                        updates_batch.append({
                            'type': 'job_final_update',
                            'job_id': job_id,
                            'status': current_status,
                            'percent': job['progress'].get('percent', 0),
                            'bytes_transferred': job['progress'].get('bytes_transferred', 0),
                            'total_bytes': job['progress'].get('total_bytes', 0),
                            'deletion': job['progress'].get('deletion', {})
                        })
                        logging.info(f"Prepared final update for job {job_id}: {current_status}")

                    # Update state tracking
                    previous_states[job_id] = current_status

                # Broadcast all updates in a single batch
                for update in updates_batch:
                    await manager.broadcast(update)

                # Sleep for 1 second before next check when jobs are running
                await asyncio.sleep(1)
            else:
                # No running jobs - sleep longer to reduce CPU usage (5 seconds)
                # Still do periodic cleanup
                cleanup_counter += 1
                if cleanup_counter >= 10:
                    cleaned = job_manager.cleanup_stopped_engines()
                    if cleaned > 0:
                        logging.info(f"Cleaned up {cleaned} stopped engine(s)")
                    cleanup_counter = 0

                await asyncio.sleep(5)

        except Exception as e:
            logging.error(f"Error in monitor_jobs_task: {e}")

            # Log error to database (Task 6.5)
            try:
                error_repo = get_error_repository()
                error_event = ErrorEvent.from_exception(
                    exception=e,
                    severity=ErrorEvent.SEVERITY_HIGH,
                    component=ErrorEvent.COMPONENT_BACKGROUND_MONITOR,
                    message='Background job monitoring encountered an error'
                )
                error_repo.log_error(error_event)
            except Exception as log_err:
                logging.error(f"Failed to log error event: {log_err}")

            # Notify users of background task failure
            try:
                await manager.broadcast_notification(
                    'error',
                    'Background job monitoring encountered an error',
                    f'{str(e)}'
                )
            except Exception:
                pass  # Don't let notification failure crash the monitor
            await asyncio.sleep(1)  # Continue after error


async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint handler for real-time job updates.
    Keeps connection alive and handles client disconnection.
    """
    await manager.connect(websocket)

    try:
        # Send initial connection confirmation
        await websocket.send_json({
            'type': 'connection_response',
            'status': 'connected'
        })

        # Keep connection alive, listen for client messages if needed
        while True:
            # Receive any client messages (optional, can be used for ping/pong)
            data = await websocket.receive_text()
            # Could handle client commands here if needed

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        import logging
        logging.error(f"WebSocket error: {e}")

        # Log error to database (Task 6.5)
        try:
            error_repo = get_error_repository()
            error_event = ErrorEvent.from_exception(
                exception=e,
                severity=ErrorEvent.SEVERITY_MEDIUM,
                component=ErrorEvent.COMPONENT_WEBSOCKET,
                message='WebSocket connection error'
            )
            error_repo.log_error(error_event)
        except Exception as log_err:
            logging.error(f"Failed to log error event: {log_err}")

        manager.disconnect(websocket)


async def start_log_indexer():
    """
    Start the log indexer background task.
    Indexes log files into SQLite database every 30 seconds.
    """
    global log_indexer

    try:
        log_indexer = LogIndexer(interval=30)
        await log_indexer.start()
        import logging
        logging.info("Log indexer background task started")
    except Exception as e:
        import logging
        logging.error(f"Failed to start log indexer: {e}")
        log_indexer = None

        # Log error to database (Task 6.5)
        try:
            error_repo = get_error_repository()
            error_event = ErrorEvent.from_exception(
                exception=e,
                severity=ErrorEvent.SEVERITY_MEDIUM,
                component='log_indexer',
                message='Log indexer failed to start'
            )
            error_repo.log_error(error_event)
        except Exception as log_err:
            logging.error(f"Failed to log error event: {log_err}")

        # Notify users of log indexer startup failure
        try:
            await manager.broadcast_notification(
                'warning',
                'Log indexer failed to start',
                f'Log search functionality may be limited. Error: {str(e)}'
            )
        except Exception:
            pass


async def stop_log_indexer():
    """
    Stop the log indexer background task.
    Called on application shutdown.
    """
    global log_indexer

    if log_indexer:
        try:
            await log_indexer.stop()
            import logging
            logging.info("Log indexer stopped")
        except Exception as e:
            import logging
            logging.error(f"Error stopping log indexer: {e}")
