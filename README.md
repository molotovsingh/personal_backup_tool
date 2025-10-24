# Backup Manager

A robust GUI tool for managing file backups from local/network drives to network shares or Google Drive. Built with resilience and reliability in mind.

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
uv run streamlit run app.py
```

The app will open at http://localhost:8501

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
├── app.py                    # Main Streamlit application
├── models/
│   └── job.py               # Job data model
├── storage/
│   └── job_storage.py       # YAML persistence
├── core/
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

For a better development experience with faster auto-reload:

```bash
# Install development dependencies (optional)
uv pip install -r requirements-dev.txt
```

This installs **watchdog**, which provides faster file system monitoring for Streamlit's auto-reload feature. While not required, it significantly improves the development workflow.

### Running Tests

```bash
# Test individual components
uv run test_job_model.py
uv run test_storage.py
uv run test_job_manager.py
uv run test_network_monitor.py
uv run test_rclone_helper.py
```

### Adding New Features

1. Follow the existing architecture
2. Add models in `models/`
3. Add business logic in `core/`
4. Update UI in `app.py`
5. Test thoroughly with `TESTING.md`

## License

MIT

## Credits

Built with:
- [Streamlit](https://streamlit.io/) - Web framework
- [rsync](https://rsync.samba.org/) - Local/network sync
- [rclone](https://rclone.org/) - Cloud storage sync
- [PyYAML](https://pyyaml.org/) - Configuration storage

---

**Version**: 1.0.0
**Last Updated**: 2025-10-24
