"""
Backup Manager - GUI for managing local and cloud backups
"""
import streamlit as st
import os
from pathlib import Path
from core.job_manager import JobManager
from core.settings import get_settings
from utils.rclone_helper import list_remotes, is_rclone_installed
from utils.file_browser import show_path_input_with_browser, show_network_shares_selector, show_smb_discovery
from utils.network_discovery import get_all_network_shares


def read_last_lines(file_path, n=5, max_bytes=8192):
    """
    Efficiently read the last N lines from a file without loading the entire file.

    Args:
        file_path: Path to the file
        n: Number of lines to read from end
        max_bytes: Maximum bytes to read from end (default 8KB should be enough for most logs)

    Returns:
        List of last N lines
    """
    try:
        with open(file_path, 'rb') as f:
            # Get file size
            f.seek(0, 2)  # Seek to end
            file_size = f.tell()

            # Read from the end
            bytes_to_read = min(max_bytes, file_size)
            f.seek(file_size - bytes_to_read)

            # Read and decode
            content = f.read().decode('utf-8', errors='ignore')
            lines = content.splitlines()

            # Return last N lines
            return lines[-n:] if len(lines) >= n else lines
    except Exception as e:
        return []


# Page config
st.set_page_config(
    page_title="Backup Manager",
    page_icon="💾",
    layout="wide"
)

# Check for interrupted jobs on startup (crash recovery)
if 'startup_check_done' not in st.session_state:
    st.session_state.startup_check_done = True

    # Check for running jobs
    manager = JobManager()
    jobs = manager.list_jobs()
    interrupted_jobs = [job for job in jobs if job['status'] == 'running']

    if interrupted_jobs:
        st.session_state.interrupted_jobs = interrupted_jobs
        st.session_state.show_recovery_prompt = True
    else:
        st.session_state.show_recovery_prompt = False

    # Check for rclone installation
    rclone_installed, _ = is_rclone_installed()
    st.session_state.rclone_installed = rclone_installed

    # Auto-resume paused jobs if setting is enabled
    settings = get_settings()
    if settings.get('auto_start_on_launch', False):
        paused_jobs = [job for job in jobs if job['status'] == 'paused']
        if paused_jobs:
            st.session_state.auto_resumed_jobs = []
            for job in paused_jobs:
                success, message = manager.start_job(job['id'])
                if success:
                    st.session_state.auto_resumed_jobs.append(job['name'])
            if st.session_state.auto_resumed_jobs:
                st.session_state.show_auto_resume_message = True

# Sidebar navigation
st.sidebar.title("💾 Backup Manager")

# Show rclone warning if not installed
if not st.session_state.get('rclone_installed', False):
    st.sidebar.warning("⚠️ rclone not installed")
    st.sidebar.caption("Cloud backup disabled. Run: `brew install rclone`")

page = st.sidebar.radio(
    "Navigation",
    ["Dashboard", "Jobs", "Settings", "Logs"]
)

# Show crash recovery prompt if needed
if st.session_state.get('show_recovery_prompt', False):
    interrupted_count = len(st.session_state.get('interrupted_jobs', []))

    st.sidebar.markdown("---")
    st.sidebar.warning(f"⚠️ {interrupted_count} interrupted job(s) found")

    if st.sidebar.button("Resume Interrupted Jobs"):
        manager = JobManager()
        resumed = 0
        for job in st.session_state.interrupted_jobs:
            # Mark as paused first
            job_obj = manager.storage.get_job(job['id'])
            if job_obj:
                job_obj.update_status('paused')
                manager.storage.update_job(job_obj)
                resumed += 1

        st.session_state.show_recovery_prompt = False
        st.sidebar.success(f"✓ Marked {resumed} job(s) as paused. You can restart them manually.")
        st.rerun()

    if st.sidebar.button("Ignore"):
        # Mark all as paused
        manager = JobManager()
        for job in st.session_state.interrupted_jobs:
            job_obj = manager.storage.get_job(job['id'])
            if job_obj:
                job_obj.update_status('paused')
                manager.storage.update_job(job_obj)

        st.session_state.show_recovery_prompt = False
        st.rerun()

# Show auto-resume message if jobs were auto-started
if st.session_state.get('show_auto_resume_message', False):
    auto_resumed = st.session_state.get('auto_resumed_jobs', [])
    if auto_resumed:
        st.sidebar.markdown("---")
        st.sidebar.info(f"▶️ Auto-resumed {len(auto_resumed)} paused job(s)")
        if st.sidebar.button("Dismiss"):
            st.session_state.show_auto_resume_message = False
            st.rerun()

# Main content
if page == "Dashboard":
    st.title("Dashboard")

    # Get jobs for display
    manager = JobManager()
    jobs = manager.list_jobs()

    # Check if any jobs are running (for auto-refresh at end)
    has_running_jobs = any(job['status'] == 'running' for job in jobs)

    # Calculate live stats
    active_jobs_count = sum(1 for job in jobs if job['status'] == 'running')
    total_bytes = sum(job['progress'].get('bytes_transferred', 0) for job in jobs)

    # Convert to appropriate unit
    if total_bytes > 1024**4:
        total_transferred_str = f"{total_bytes / 1024**4:.2f} TB"
    elif total_bytes > 1024**3:
        total_transferred_str = f"{total_bytes / 1024**3:.2f} GB"
    elif total_bytes > 1024**2:
        total_transferred_str = f"{total_bytes / 1024**2:.2f} MB"
    else:
        total_transferred_str = f"{total_bytes / 1024:.2f} KB"

    # Check network status using socket connection
    import socket
    try:
        # Try to connect to Google DNS on port 53 (more portable than ping)
        socket.create_connection(('8.8.8.8', 53), timeout=2)
        network_online = True
    except (socket.timeout, socket.error, OSError):
        network_online = False
    except Exception as e:
        # Log unexpected errors but don't crash
        import logging
        logging.warning(f"Unexpected error checking network: {e}")
        network_online = False

    network_status = "✅ Online" if network_online else "❌ Offline"

    # Display stats
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Active Jobs", active_jobs_count, delta=None)
    with col2:
        st.metric("Total Transferred", total_transferred_str)
    with col3:
        st.metric("Network Status", network_status)

    st.markdown("---")

    # Active jobs panel
    st.subheader("Active Jobs")

    running_jobs = [job for job in jobs if job['status'] == 'running']

    if not running_jobs:
        st.info("No jobs currently running")
    else:
        for job in running_jobs:
            progress = job['progress']
            percent = progress.get('percent', 0)

            # Job card
            with st.container():
                col1, col2 = st.columns([3, 1])

                with col1:
                    st.write(f"**{job['name']}** ({job['type']})")
                    # Progress bar (text param separated for compatibility with older Streamlit)
                    st.progress(percent / 100.0 if percent <= 100 else 1.0)
                    st.caption(f"{percent}%")

                with col2:
                    # Speed
                    speed_bytes = progress.get('speed_bytes', 0)
                    if speed_bytes > 1024**2:
                        speed_str = f"{speed_bytes / 1024**2:.2f} MB/s"
                    elif speed_bytes > 1024:
                        speed_str = f"{speed_bytes / 1024:.2f} KB/s"
                    else:
                        speed_str = f"{speed_bytes} B/s"
                    st.metric("Speed", speed_str, label_visibility="collapsed")

                # Stats row
                col1, col2, col3 = st.columns(3)

                with col1:
                    bytes_transferred = progress.get('bytes_transferred', 0)
                    if bytes_transferred > 1024**3:
                        transferred_str = f"{bytes_transferred / 1024**3:.2f} GB"
                    elif bytes_transferred > 1024**2:
                        transferred_str = f"{bytes_transferred / 1024**2:.2f} MB"
                    else:
                        transferred_str = f"{bytes_transferred / 1024:.2f} KB"
                    st.caption(f"📦 Transferred: {transferred_str}")

                with col2:
                    st.caption(f"📊 Progress: {percent}%")

                with col3:
                    eta_seconds = progress.get('eta_seconds', 0)
                    if eta_seconds > 3600:
                        eta_str = f"{eta_seconds // 3600}h {(eta_seconds % 3600) // 60}m"
                    elif eta_seconds > 60:
                        eta_str = f"{eta_seconds // 60}m {eta_seconds % 60}s"
                    else:
                        eta_str = f"{eta_seconds}s"
                    st.caption(f"⏱️ ETA: {eta_str}")

                st.markdown("---")

    st.markdown("---")
    st.subheader("Recent Activity")

    # Gather recent events from job logs
    log_dir = Path.home() / "backup-manager" / "logs"
    events = []

    if log_dir.exists():
        # Read all log files and extract key events
        for log_file in sorted(log_dir.glob("*.log"), key=lambda p: p.stat().st_mtime, reverse=True):
            try:
                # Efficiently read last 5 lines without loading entire file
                lines = read_last_lines(log_file, n=5)
                for line in lines:
                        # Parse log line format: [2025-01-15 10:30:45] message
                        if line.strip() and '[' in line:
                            try:
                                timestamp_end = line.index(']')
                                timestamp = line[1:timestamp_end]
                                message = line[timestamp_end+2:].strip()

                                # Filter for important events
                                if any(keyword in message.lower() for keyword in [
                                    'starting', 'completed', 'failed', 'stopped', 'error'
                                ]):
                                    # Extract job name from log filename
                                    job_name = log_file.stem.replace('rsync_', '').replace('rclone_', '')

                                    # Determine event type
                                    if 'starting' in message.lower():
                                        event_icon = '▶️'
                                        event_type = 'Started'
                                    elif 'completed' in message.lower():
                                        event_icon = '✅'
                                        event_type = 'Completed'
                                    elif 'failed' in message.lower() or 'error' in message.lower():
                                        event_icon = '❌'
                                        event_type = 'Failed'
                                    elif 'stopped' in message.lower():
                                        event_icon = '⏸️'
                                        event_type = 'Stopped'
                                    else:
                                        event_icon = 'ℹ️'
                                        event_type = 'Info'

                                    events.append({
                                        'timestamp': timestamp,
                                        'job': job_name[:8],  # Show first 8 chars of job ID
                                        'type': event_type,
                                        'icon': event_icon,
                                        'message': message[:80]  # Truncate long messages
                                    })
                            except (ValueError, IndexError) as e:
                                # Skip malformed log lines
                                continue
            except (OSError, IOError, PermissionError) as e:
                # Skip files that can't be read
                continue

    # Sort by timestamp (most recent first) and limit to 10
    events.sort(key=lambda x: x['timestamp'], reverse=True)
    events = events[:10]

    if not events:
        st.info("No recent activity")
    else:
        # Display events in a table-like format
        for event in events:
            col1, col2, col3 = st.columns([1, 2, 5])

            with col1:
                st.caption(event['timestamp'][-8:])  # Show only time (HH:MM:SS)

            with col2:
                st.caption(f"{event['icon']} {event['type']}")

            with col3:
                st.caption(f"Job {event['job']}: {event['message']}")

    # Auto-refresh at end of page if there are running jobs
    if has_running_jobs:
        import time
        settings = get_settings()
        refresh_interval = settings.get('auto_refresh_interval', 2)  # Default 2 seconds
        time.sleep(refresh_interval)
        st.rerun()

elif page == "Jobs":
    st.title("Backup Jobs")

    # Get jobs and check if any are running (for auto-refresh at end)
    manager = JobManager()
    jobs_list = manager.list_jobs()
    has_running_jobs_on_jobs_page = any(job['status'] == 'running' for job in jobs_list)

    # Initialize session state for form visibility
    if 'show_create_form' not in st.session_state:
        st.session_state.show_create_form = False

    # Toggle form button
    col1, col2 = st.columns([1, 5])
    with col1:
        if st.button("➕ New Job" if not st.session_state.show_create_form else "❌ Cancel"):
            st.session_state.show_create_form = not st.session_state.show_create_form
            st.rerun()

    # Show form if toggled
    if st.session_state.show_create_form:
        st.markdown("### Create New Backup Job")

        # Initialize session state for path selection
        if 'selected_source_path' not in st.session_state:
            st.session_state.selected_source_path = ""
        if 'selected_dest_path' not in st.session_state:
            st.session_state.selected_dest_path = ""
        if 'show_source_browser' not in st.session_state:
            st.session_state.show_source_browser = False
        if 'show_dest_browser' not in st.session_state:
            st.session_state.show_dest_browser = False

        # Browse for Source Path
        st.markdown("#### 📁 Source Path")
        col1, col2 = st.columns([3, 1])
        with col1:
            if st.session_state.selected_source_path:
                st.success(f"Selected: `{st.session_state.selected_source_path}`")
            else:
                st.info("Click 'Browse' to select source directory")
        with col2:
            if st.button("📁 Browse", key="browse_source_btn", use_container_width=True):
                st.session_state.show_source_browser = not st.session_state.show_source_browser
                st.rerun()

        if st.session_state.show_source_browser:
            with st.expander("📂 Select Source Location", expanded=True):
                from utils.file_browser import show_file_browser

                source_tab1, source_tab2 = st.tabs(["📁 Browse Files", "🌐 Network Shares"])

                with source_tab1:
                    st.caption("Navigate to the folder you want to backup")
                    browsed_source = show_file_browser(
                        key="source_browser",
                        initial_path=st.session_state.selected_source_path or None,
                        mode="directory"
                    )
                    if browsed_source:
                        if st.button("✓ Use This Path", key="confirm_source_browse", use_container_width=True):
                            st.session_state.selected_source_path = browsed_source
                            st.session_state.show_source_browser = False
                            st.rerun()

                with source_tab2:
                    st.caption("Select from mounted network shares")
                    source_share = show_network_shares_selector("source_shares")
                    if source_share:
                        if st.button("✓ Use This Share", key="confirm_source_share", use_container_width=True):
                            st.session_state.selected_source_path = source_share
                            st.session_state.show_source_browser = False
                            st.rerun()

        # Browse for Destination Path
        st.markdown("#### 📁 Destination Path")
        col1, col2 = st.columns([3, 1])
        with col1:
            if st.session_state.selected_dest_path:
                st.success(f"Selected: `{st.session_state.selected_dest_path}`")
            else:
                st.info("Click 'Browse' to select destination directory")
        with col2:
            if st.button("📁 Browse", key="browse_dest_btn", use_container_width=True):
                st.session_state.show_dest_browser = not st.session_state.show_dest_browser
                st.rerun()

        if st.session_state.show_dest_browser:
            with st.expander("📂 Select Destination Location", expanded=True):
                from utils.file_browser import show_file_browser

                dest_tab1, dest_tab2 = st.tabs(["📁 Browse Files", "🌐 Network Shares"])

                with dest_tab1:
                    st.caption("Navigate to where you want to save the backup")
                    browsed_dest = show_file_browser(
                        key="dest_browser",
                        initial_path=st.session_state.selected_dest_path or None,
                        mode="directory"
                    )
                    if browsed_dest:
                        if st.button("✓ Use This Path", key="confirm_dest_browse", use_container_width=True):
                            st.session_state.selected_dest_path = browsed_dest
                            st.session_state.show_dest_browser = False
                            st.rerun()

                with dest_tab2:
                    st.caption("Select from mounted network shares")
                    dest_share = show_network_shares_selector("dest_shares")
                    if dest_share:
                        if st.button("✓ Use This Share", key="confirm_dest_share", use_container_width=True):
                            st.session_state.selected_dest_path = dest_share
                            st.session_state.show_dest_browser = False
                            st.rerun()

        st.markdown("---")

        with st.form("create_job_form"):
            # Job name
            job_name = st.text_input(
                "Job Name *",
                placeholder="e.g., Photos Backup",
                help="A descriptive name for this backup job"
            )

            # Job type selection
            job_type = st.radio(
                "Backup Type *",
                options=["rsync", "rclone"],
                help="rsync: Local/network transfers | rclone: Cloud storage transfers"
            )

            # Source and destination
            col1, col2 = st.columns(2)

            with col1:
                source_path = st.text_input(
                    "Source Path *",
                    value=st.session_state.selected_source_path,
                    placeholder="/path/to/source" if job_type == "rsync" else "remote:path or /local/path",
                    help="Path to backup from (selected via Browse button above, or type manually)"
                )

            with col2:
                if job_type == "rclone":
                    # For rclone, show remote selector if available
                    remotes = list_remotes()
                    if remotes:
                        use_remote = st.checkbox("Use configured remote")
                        if use_remote:
                            selected_remote = st.selectbox("Select Remote", remotes)
                            remote_path = st.text_input(
                                "Remote Path *",
                                placeholder="path/on/remote (required)",
                                help="Specify a path on the remote. Empty path would backup to remote root."
                            )
                            # Warn if remote_path is empty
                            if not remote_path.strip():
                                st.warning("⚠️ Remote path is empty - this will backup to the remote root directory. Please specify a path.")
                                dest_path = ""  # Don't allow empty remote path
                            else:
                                dest_path = f"{selected_remote}:{remote_path.strip()}"
                        else:
                            dest_path = st.text_input(
                                "Destination Path *",
                                value=st.session_state.selected_dest_path,
                                placeholder="remote:path or /local/path",
                                help="Path to backup to (selected via Browse button above, or type manually)"
                            )
                    else:
                        dest_path = st.text_input(
                            "Destination Path *",
                            value=st.session_state.selected_dest_path,
                            placeholder="remote:path or /local/path",
                            help="Path to backup to (configure remotes with: rclone config, or use Browse button above)"
                        )
                else:
                    dest_path = st.text_input(
                        "Destination Path *",
                        value=st.session_state.selected_dest_path,
                        placeholder="/path/to/destination",
                        help="Path to backup to (selected via Browse button above, or type manually)"
                    )

            # Bandwidth limit
            use_bandwidth_limit = st.checkbox("Set Bandwidth Limit")
            bandwidth_limit = None
            if use_bandwidth_limit:
                bandwidth_limit = st.slider(
                    "Bandwidth Limit (KB/s)",
                    min_value=100,
                    max_value=10000,
                    value=1000,
                    step=100,
                    help="Maximum transfer speed in KB/s"
                )

            # Form submission
            col1, col2 = st.columns([1, 1])
            with col1:
                submit_button = st.form_submit_button("Create Job", use_container_width=True)

            if submit_button:
                # Validate inputs
                errors = []
                if not job_name or not job_name.strip():
                    errors.append("Job name is required")
                if not source_path or not source_path.strip():
                    errors.append("Source path is required")
                if not dest_path or not dest_path.strip():
                    errors.append("Destination path is required")

                if errors:
                    for error in errors:
                        st.error(error)
                else:
                    # Create job via JobManager
                    manager = JobManager()
                    settings = {}
                    if bandwidth_limit:
                        settings['bandwidth_limit'] = bandwidth_limit

                    success, msg, job = manager.create_job(
                        name=job_name.strip(),
                        source=source_path.strip(),
                        dest=dest_path.strip(),
                        job_type=job_type,
                        settings=settings
                    )

                    if success:
                        st.success(f"✓ {msg} (ID: {job.id[:8]})")
                        # Clear path selections
                        st.session_state.selected_source_path = ""
                        st.session_state.selected_dest_path = ""
                        st.session_state.show_create_form = False
                        st.rerun()
                    else:
                        st.error(f"✗ {msg}")

        # Show rclone info if needed
        if job_type == "rclone":
            is_installed, _ = is_rclone_installed()
            if not is_installed:
                st.warning("⚠️ rclone is not installed. Install with: `brew install rclone`")
            elif not list_remotes():
                st.info("ℹ️ No rclone remotes configured. Run `rclone config` to set up cloud storage.")

    st.markdown("---")

    # Job list
    st.markdown("### Backup Jobs")

    if not jobs_list:
        st.info("No jobs configured yet. Click 'New Job' to create one.")
    else:
        # Display each job in an expandable container
        for job in jobs_list:
            # Status badge colors
            status_colors = {
                'pending': '⚪',
                'running': '🔵',
                'paused': '🟡',
                'completed': '🟢',
                'failed': '🔴'
            }

            status_icon = status_colors.get(job['status'], '⚪')

            # Main job card
            with st.expander(
                f"{status_icon} **{job['name']}** - {job['type']} - {job['status']}",
                expanded=(job['status'] == 'running')
            ):
                # Job details
                col1, col2 = st.columns(2)

                with col1:
                    st.write(f"**Source:** `{job['source']}`")
                    st.write(f"**Destination:** `{job['dest']}`")
                    st.write(f"**Type:** {job['type']}")

                with col2:
                    st.write(f"**Status:** {job['status']}")
                    st.write(f"**Created:** {job['created_at'][:19]}")
                    st.write(f"**Updated:** {job['updated_at'][:19]}")

                # Show error information for failed jobs
                if job['status'] == 'failed':
                    st.markdown("---")
                    # Try to read last few lines from log file to show error
                    log_file = Path.home() / 'backup-manager' / 'logs' / f"{job['type']}_{job['id']}.log"
                    if log_file.exists():
                        error_lines = read_last_lines(log_file, n=3)
                        if error_lines:
                            error_msg = "\n".join(error_lines)
                            st.error(f"**❌ Job Failed**\n\n```\n{error_msg}\n```")
                        else:
                            st.error("**❌ Job Failed** - Check logs for details")
                    else:
                        st.error("**❌ Job Failed** - Log file not found")

                    # Show link to full logs
                    st.caption("💡 Click 'Retry' to try again, or view full logs in the Logs page")

                # Progress information
                if job['status'] in ['running', 'completed', 'paused', 'failed']:
                    st.markdown("---")
                    progress = job['progress']

                    # Show pause indicator for paused jobs
                    if job['status'] == 'paused':
                        percent = progress.get('percent', 0)
                        bytes_transferred = progress.get('bytes_transferred', 0)
                        if bytes_transferred > 1024**3:
                            size_str = f"{bytes_transferred / 1024**3:.2f} GB"
                        elif bytes_transferred > 1024**2:
                            size_str = f"{bytes_transferred / 1024**2:.2f} MB"
                        else:
                            size_str = f"{bytes_transferred / 1024:.2f} KB"

                        st.info(f"⏸️ **Paused at {percent}%** - {size_str} transferred. Click Resume to continue.")

                    # Progress bar
                    percent = progress.get('percent', 0)
                    st.progress(percent / 100.0 if percent <= 100 else 1.0)

                    # Stats
                    col1, col2, col3, col4 = st.columns(4)

                    with col1:
                        bytes_transferred = progress.get('bytes_transferred', 0)
                        if bytes_transferred > 1024**3:
                            st.metric("Transferred", f"{bytes_transferred / 1024**3:.2f} GB")
                        elif bytes_transferred > 1024**2:
                            st.metric("Transferred", f"{bytes_transferred / 1024**2:.2f} MB")
                        else:
                            st.metric("Transferred", f"{bytes_transferred / 1024:.2f} KB")

                    with col2:
                        st.metric("Progress", f"{percent}%")

                    with col3:
                        speed_bytes = progress.get('speed_bytes', 0)
                        if job['status'] == 'paused':
                            st.metric("Speed", "Paused")
                        elif speed_bytes > 1024**2:
                            st.metric("Speed", f"{speed_bytes / 1024**2:.2f} MB/s")
                        elif speed_bytes > 1024:
                            st.metric("Speed", f"{speed_bytes / 1024:.2f} KB/s")
                        else:
                            st.metric("Speed", f"{speed_bytes} B/s")

                    with col4:
                        if job['status'] == 'paused':
                            st.metric("ETA", "Paused")
                        else:
                            eta_seconds = progress.get('eta_seconds', 0)
                            if eta_seconds > 3600:
                                st.metric("ETA", f"{eta_seconds // 3600}h {(eta_seconds % 3600) // 60}m")
                            elif eta_seconds > 60:
                                st.metric("ETA", f"{eta_seconds // 60}m {eta_seconds % 60}s")
                            else:
                                st.metric("ETA", f"{eta_seconds}s")

                # Control buttons
                st.markdown("---")
                col1, col2, col3, col4 = st.columns([1, 1, 1, 3])

                with col1:
                    # Start/Resume/Retry button - show for pending, paused, or failed jobs
                    if job['status'] == 'paused':
                        # Show Resume for paused jobs
                        button_label = "▶️ Resume"
                        button_help = "Resume from where the job was paused"
                    elif job['status'] == 'failed':
                        # Show Retry for failed jobs
                        button_label = "🔄 Retry"
                        button_help = "Retry this backup job from the beginning"
                    elif job['status'] == 'pending':
                        # Show Start for new jobs
                        button_label = "▶️ Start"
                        button_help = "Start this backup job"
                    else:
                        button_label = "▶️ Start"
                        button_help = None

                    if job['status'] in ['pending', 'paused', 'failed']:
                        if st.button(button_label, key=f"start_{job['id']}", use_container_width=True, help=button_help):
                            success, msg = manager.start_job(job['id'])
                            if success:
                                st.success(msg)
                                st.rerun()
                            else:
                                st.error(msg)
                    else:
                        st.button(button_label, disabled=True, key=f"start_{job['id']}_disabled", use_container_width=True)

                with col2:
                    # Pause button - only show if job is running
                    if job['status'] == 'running':
                        if st.button("⏸️ Pause", key=f"pause_{job['id']}", use_container_width=True,
                                   help="Pause this job (can be resumed later)"):
                            success, msg = manager.stop_job(job['id'])
                            if success:
                                st.success(msg)
                                st.rerun()
                            else:
                                st.error(msg)
                    else:
                        st.button("⏸️ Pause", disabled=True, key=f"pause_{job['id']}_disabled", use_container_width=True)

                with col3:
                    # Delete button - always available
                    if st.button("🗑️ Delete", key=f"delete_{job['id']}", use_container_width=True):
                        # Store delete confirmation in session state
                        if f"confirm_delete_{job['id']}" not in st.session_state:
                            st.session_state[f"confirm_delete_{job['id']}"] = True
                            st.warning(f"⚠️ Click Delete again to confirm deletion of '{job['name']}'")
                            st.rerun()
                        else:
                            success, msg = manager.delete_job(job['id'])
                            del st.session_state[f"confirm_delete_{job['id']}"]
                            if success:
                                st.success(msg)
                                st.rerun()
                            else:
                                st.error(msg)

    # Auto-refresh at end of page if there are running jobs
    if has_running_jobs_on_jobs_page:
        import time
        settings = get_settings()
        refresh_interval = settings.get('auto_refresh_interval', 2)  # Default 2 seconds
        time.sleep(refresh_interval)
        st.rerun()

elif page == "Settings":
    st.title("Settings")

    settings = get_settings()

    # Application Settings
    st.subheader("Application Settings")

    with st.form("settings_form"):
        # Default bandwidth limit
        default_bw = st.number_input(
            "Default Bandwidth Limit (KB/s)",
            min_value=0,
            max_value=100000,
            value=settings.get('default_bandwidth_limit', 0),
            step=100,
            help="0 = unlimited. This will be the default for new jobs."
        )

        # Auto-start on launch
        auto_start = st.checkbox(
            "Auto-start paused jobs on app launch",
            value=settings.get('auto_start_on_launch', False),
            help="Automatically resume paused jobs when the app starts"
        )

        # Network check interval
        network_interval = st.slider(
            "Network Check Interval (seconds)",
            min_value=10,
            max_value=300,
            value=settings.get('network_check_interval', 30),
            step=10,
            help="How often to check network connectivity"
        )

        # Max retry attempts
        max_retries = st.slider(
            "Maximum Retry Attempts",
            min_value=3,
            max_value=20,
            value=settings.get('max_retry_attempts', 10),
            help="Number of times to retry after network failure"
        )

        # Dashboard refresh interval
        refresh_interval = st.slider(
            "Dashboard Refresh Interval (seconds)",
            min_value=1,
            max_value=10,
            value=settings.get('auto_refresh_interval', 2),
            help="How often to refresh the dashboard"
        )

        col1, col2 = st.columns([1, 1])

        with col1:
            save_button = st.form_submit_button("💾 Save Settings", use_container_width=True)

        with col2:
            reset_button = st.form_submit_button("🔄 Reset to Defaults", use_container_width=True)

        if save_button:
            settings.set('default_bandwidth_limit', default_bw)
            settings.set('auto_start_on_launch', auto_start)
            settings.set('network_check_interval', network_interval)
            settings.set('max_retry_attempts', max_retries)
            settings.set('auto_refresh_interval', refresh_interval)
            st.success("✓ Settings saved successfully!")
            st.rerun()

        if reset_button:
            settings.reset_to_defaults()
            st.success("✓ Settings reset to defaults")
            st.rerun()

    st.markdown("---")

    # System Information
    st.subheader("System Information")
    st.write(f"📁 Project Directory: `{Path.home() / 'backup-manager'}`")
    st.write(f"📝 Logs Directory: `{Path.home() / 'backup-manager' / 'logs'}`")
    st.write(f"⚙️  Settings File: `{Path.home() / 'backup-manager' / 'settings.yaml'}`")
    st.write(f"💾 Jobs File: `{Path.home() / 'backup-manager' / 'jobs.yaml'}`")

    st.markdown("---")

    # Tools Check
    st.subheader("Tools Check")

    # Check rsync
    rsync_check = os.system("which rsync > /dev/null 2>&1") == 0
    st.write(f"**rsync:** {'✅ Installed' if rsync_check else '❌ Not found'}")

    # Check rclone
    rclone_check = os.system("which rclone > /dev/null 2>&1") == 0
    if rclone_check:
        remotes = list_remotes()
        st.write(f"**rclone:** ✅ Installed ({len(remotes)} remote(s) configured)")
        if remotes:
            for remote in remotes:
                st.write(f"  - {remote}")
    else:
        st.write(f"**rclone:** ❌ Not installed")
        st.info("Install with: `brew install rclone`")

elif page == "Logs":
    st.title("Logs")

    log_dir = Path.home() / "backup-manager" / "logs"
    logs = list(log_dir.glob("*.log")) if log_dir.exists() else []

    if not logs:
        st.info("No log files found")
    else:
        # Filter options
        col1, col2, col3 = st.columns([2, 2, 1])

        with col1:
            # Job filter
            job_names = ["All"] + [log.stem for log in logs]
            selected_job = st.selectbox("Filter by Job", job_names)

        with col2:
            # Search
            search_term = st.text_input("Search logs", placeholder="e.g., error, completed, retry")

        with col3:
            # Refresh button
            if st.button("🔄 Refresh"):
                st.rerun()

        # Get filtered logs
        filtered_logs = logs
        if selected_job != "All":
            filtered_logs = [log for log in logs if log.stem == selected_job]

        if not filtered_logs:
            st.warning("No logs match the filter")
        else:
            # Read and combine log contents (with limit to prevent memory issues)
            MAX_LINES_PER_FILE = 1000  # Limit lines per file to prevent memory issues
            all_lines = []
            for log in filtered_logs:
                try:
                    # Read file line by line instead of loading all at once
                    with open(log, 'r') as f:
                        # Read from end if file is large
                        f.seek(0, 2)  # Seek to end
                        file_size = f.tell()

                        if file_size > 100000:  # If file > 100KB, read last portion only
                            # Read last ~100KB for efficiency
                            f.seek(max(0, file_size - 100000))
                            f.readline()  # Skip partial line
                        else:
                            f.seek(0)  # Read from beginning for small files

                        line_count = 0
                        for line in f:
                            all_lines.append((log.stem, line))
                            line_count += 1
                            if line_count >= MAX_LINES_PER_FILE:
                                st.info(f"⚠️ Showing last {MAX_LINES_PER_FILE} lines from {log.name} (file truncated)")
                                break
                except Exception as e:
                    st.error(f"Error reading {log.name}: {e}")

            # Apply search filter
            if search_term:
                all_lines = [(job, line) for job, line in all_lines
                             if search_term.lower() in line.lower()]

            # Display results
            st.markdown(f"**Showing {len(all_lines)} line(s)**")

            if not all_lines:
                st.info("No matching log entries")
            else:
                # Export button
                col1, col2 = st.columns([1, 5])
                with col1:
                    # Create download content
                    export_content = "\n".join([f"[{job}] {line.strip()}" for job, line in all_lines])
                    st.download_button(
                        label="📥 Export",
                        data=export_content,
                        file_name=f"backup_logs_{selected_job}.txt",
                        mime="text/plain"
                    )

                st.markdown("---")

                # Display logs with syntax highlighting
                log_text = ""
                for job, line in all_lines[-500:]:  # Show last 500 lines
                    # Highlight search term
                    if search_term and search_term.lower() in line.lower():
                        log_text += f"➤ [{job}] {line}"
                    else:
                        log_text += f"  [{job}] {line}"

                st.code(log_text, language="log")

# Footer
st.sidebar.markdown("---")
st.sidebar.caption("Backup Manager v0.1")
st.sidebar.caption("Managing your backups safely")
