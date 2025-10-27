# Backup Manager

A robust web-based tool for managing file backups from local/network drives to network shares or Google Drive. Built with resilience, security, and reliability in mind.

## Features

### Core Functionality
- ✅ **Dual-Engine Support**: rsync for local/network transfers, rclone for cloud storage
- ✅ **Real-time Monitoring**: Live progress tracking with speed, ETA, and bytes transferred
- ✅ **Interactive Dashboard**: Visual overview of all active jobs and recent activity
- ✅ **Job Management**: Create, start, stop, and delete backup jobs via intuitive UI

### Resilience & Recovery
- ✅ **Auto-Reconnect**: Automatic retry with exponential backoff on network failures (up to 10 attempts)
- ✅ **Resume Support**: Continue interrupted transfers from where they stopped
- ✅ **Crash Recovery**: Detect and resume jobs interrupted by app crashes or power loss
- ✅ **Network Monitoring**: Background connectivity checking with configurable intervals

### Advanced Features
- ✅ **Bandwidth Limiting**: Control transfer speeds to prevent network saturation
- ✅ **Disk Space Validation**: Pre-flight checks to ensure sufficient space
- ✅ **Enhanced Logging**: Filter, search, and export logs for troubleshooting
- ✅ **Persistent Storage**: YAML-based job and settings storage
- ✅ **Configurable Settings**: Customize retry attempts, check intervals, and defaults

## Installation

### Prerequisites
- Python 3.9+
- rsync (usually pre-installed on macOS/Linux)
- rclone (optional, for cloud storage)

### Setup

```bash
# Clone or navigate to the project
cd ~/backup-manager

# Create virtual environment with uv
uv venv

# Install dependencies
uv pip install -r requirements.txt

# Install rclone (if using cloud storage)
brew install rclone

# Configure rclone for cloud providers
rclone config
```

## Quick Start

### 1. Launch the App

```bash
# Development mode (with debug logging and auto-reload)
uv run uvicorn fastapi_app:app --host 0.0.0.0 --port 5001 --reload

# Production mode (requires SECRET_KEY environment variable)
export SECRET_KEY=$(python -c 'import secrets; print(secrets.token_hex(32))')
uv run uvicorn fastapi_app:app --host 0.0.0.0 --port 5001
```

The app will be available at http://localhost:5001

### 2. Create Your First Job

1. Navigate to **Jobs** page
2. Click **"➕ New Job"**
3. Fill in the details:
   - **Name**: Descriptive name for your backup
   - **Type**: Choose `rsync` (local/network) or `rclone` (cloud)
   - **Source**: Path to backup from
   - **Destination**: Where to backup to
4. (Optional) Set bandwidth limit
5. Click **"Create Job"**

### 3. Start Backing Up

1. Find your job in the list
2. Click **"▶️ Start"**
3. Monitor progress on the **Dashboard**

### 4. Configure Your Specific Jobs

Use the setup script to configure the jobs mentioned in your use case:

```bash
uv run setup_jobs.py
```

This will guide you through setting up:
- **Photos Backup** (509GB): Seagate → MacBook network
- **Arq Backup** (343GB): Seagate → Google Drive

## Project Structure

```
backup-manager/
├── fastapi_app/             # FastAPI web application
│   ├── __init__.py          # App initialization with middleware
│   ├── routers/             # API routers
│   │   ├── dashboard.py     # Dashboard endpoints
│   │   ├── jobs.py          # Job management endpoints
│   │   ├── settings.py      # Settings endpoints
│   │   └── logs.py          # Logs endpoints
│   ├── websocket/           # WebSocket support
│   │   └── manager.py       # Connection manager
│   ├── background.py        # Background tasks
│   └── templates/           # Jinja2 HTML templates (from flask_app/)
│       ├── base.html        # Base template
│       ├── dashboard.html   # Dashboard page
│       ├── jobs.html        # Jobs management page
│       ├── settings.html    # Settings page
│       └── logs.html        # Logs viewer page
├── models/
│   └── job.py               # Job data model
├── storage/
│   └── job_storage.py       # YAML persistence
├── core/
│   ├── paths.py             # Centralized path management
│   ├── job_manager.py       # Job orchestration
│   ├── network_monitor.py   # Network connectivity monitoring
│   └── settings.py          # Application settings
├── engines/
│   ├── rsync_engine.py      # rsync wrapper with auto-retry
│   └── rclone_engine.py     # rclone wrapper with auto-retry
├── utils/
│   ├── rclone_helper.py     # rclone configuration helpers
│   └── validation.py        # Pre-flight validation utilities
└── ~/backup-manager/        # User data (created at runtime)
    ├── jobs.yaml            # Job configurations
    ├── settings.yaml        # User settings
    └── logs/                # Job execution logs
```

## Usage Guide

### Dashboard
- **Live Stats**: Active jobs, total transferred, network status
- **Active Jobs Panel**: Real-time progress of running transfers
- **Recent Activity**: Last 10 significant events across all jobs

### Jobs Page
- **Create Jobs**: Add new backup configurations
- **Job List**: View all jobs with status badges
- **Controls**: Start/stop/delete jobs with confirmation
- **Progress Details**: Expandable cards show detailed transfer info

### Settings Page
- **Application Settings**: Configure defaults and behavior
  - Default bandwidth limit
  - Auto-start on launch
  - Network check interval
  - Max retry attempts
  - Dashboard refresh rate
- **System Information**: View data directory locations
- **Tools Check**: Verify rsync and rclone installation

### Logs Page
- **Filter by Job**: View logs for specific jobs
- **Search**: Find specific events or errors
- **Export**: Download filtered logs
- **Refresh**: Manually update log view

## Testing

Run the comprehensive test suite:

```bash
# See TESTING.md for detailed test scenarios
cat TESTING.md
```

**Test coverage includes**:
- Basic job creation and execution
- Progress monitoring
- Stop/resume functionality
- Crash recovery
- Network failure handling
- Cloud storage integration
- Settings persistence
- Log management

## Troubleshooting

### Job Won't Start
- Check logs for specific errors
- Verify source and destination paths exist
- Ensure sufficient disk space
- For rclone: verify remote is configured

### Transfer Keeps Failing
- Check network connectivity
- Review logs for error patterns
- Increase max retry attempts in Settings
- Verify destination is writable

### App Crashed During Transfer
- Simply restart the app
- Look for the recovery prompt in sidebar
- Click "Resume Interrupted Jobs"
- Jobs will continue from where they stopped

## Security Configuration

### Production Deployment

For production deployments, the following security features are enabled:

1. **SECRET_KEY**: Must be set via environment variable
   ```bash
   export SECRET_KEY=$(python -c 'import secrets; print(secrets.token_hex(32))')
   ```

2. **CSRF Protection**: Enabled via FastAPI middleware
   - All mutating operations require CSRF tokens
   - HTMX requests automatically include CSRF headers

3. **CORS**: Restricted to specific origins
   ```bash
   export CORS_ALLOWED_ORIGINS="http://localhost:5001,http://127.0.0.1:5001"
   ```

4. **Session Security**: HTTPOnly, SameSite, and Secure flags enabled in production

5. **Data Directory**: Configurable via environment variable
   ```bash
   export BACKUP_MANAGER_DATA_DIR="/path/to/data"
   ```

### Development vs Production

The application automatically adjusts security settings based on the environment:

| Feature | Development | Production |
|---------|-------------|------------|
| Debug Mode | ON | OFF |
| SECRET_KEY | Default (insecure) | Required env var |
| CSRF Protection | Enabled | Enabled |
| CORS | localhost only | Configurable |
| Session Cookies | HTTP | HTTPS only |
| WebSocket Logging | Enabled | Disabled |

## Configuration Files

### jobs.yaml
Stores all job configurations:
```yaml
jobs:
  - id: abc123
    name: My Backup
    source: /path/to/source
    dest: /path/to/dest
    type: rsync
    status: pending
    progress: {...}
    settings: {...}
```

### settings.yaml
Application preferences:
```yaml
default_bandwidth_limit: 5000
auto_start_on_launch: false
network_check_interval: 30
max_retry_attempts: 10
auto_refresh_interval: 2
```

## Development

### Development Setup

The FastAPI application uses Uvicorn's hot-reloading in development mode:

```bash
# Run in development mode (debug enabled, auto-reload)
uv run uvicorn fastapi_app:app --host 0.0.0.0 --port 5001 --reload
```

Uvicorn will automatically reload on code changes.

### Running Tests

```bash
# Run pytest test suite
uv run pytest

# Test individual components
uv run pytest tests/test_job_model.py
uv run pytest tests/test_storage.py
uv run pytest tests/test_job_manager.py
```

### Adding New Features

1. Follow the existing architecture
2. Add models in `models/`
3. Add business logic in `core/`
4. Add routes in `fastapi_app/routers/`
5. Update templates in `fastapi_app/templates/`
6. Test thoroughly with pytest and manual testing

## License

MIT

## Credits

Built with:
- [FastAPI](https://fastapi.tiangolo.com/) - Modern async web framework
- [Uvicorn](https://www.uvicorn.org/) - Lightning-fast ASGI server
- [HTMX](https://htmx.org/) - Dynamic HTML without JavaScript complexity
- [Tailwind CSS](https://tailwindcss.com/) - Utility-first CSS framework
- [rsync](https://rsync.samba.org/) - Local/network sync
- [rclone](https://rclone.org/) - Cloud storage sync
- [PyYAML](https://pyyaml.org/) - Configuration storage

---

**Version**: 2.0.0
**Last Updated**: 2025-10-27
