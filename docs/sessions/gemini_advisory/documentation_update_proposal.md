# Proposal: Documentation Update (README.md)

This document proposes a revised version of the project's `README.md` file. The current version is outdated since the migration from Streamlit to Flask, and it is more verbose than necessary.

## 1. Analysis of the Current `README.md`

*   **Inaccurate Instructions:** The "Quick Start" and "Installation" sections refer to the old Streamlit application (`app.py`, `streamlit run`, port 8501), which will confuse new users.
*   **Outdated Project Structure:** The architecture diagram is for the old single-file Streamlit app and does not reflect the new, modular Flask structure.
*   **Verbose Content:** The "Features" and "Usage Guide" sections are very detailed. While comprehensive, they can be overwhelming for a user who wants a quick overview. The core value can be communicated more concisely.
*   **Irrelevant Information:** References to Streamlit-specific development features (like `watchdog` for auto-reload) are no longer relevant.

## 2. Proposed `README.md` Revision

Below is a revised `README.md` that addresses these issues. It is more accurate, concise, and reflects the current state of the Flask application.

---

# Backup Manager

A robust web-based GUI for managing local and cloud backups using `rsync` and `rclone`.

## Features

*   **Dual-Engine Support**: Use `rsync` for local/network transfers and `rclone` for cloud storage (e.g., Google Drive).
*   **Real-time Monitoring**: A live dashboard with progress tracking, transfer speed, and ETA.
*   **Full Job Management**: Create, start, stop, and delete backup jobs through an intuitive UI.
*   **Resilience & Recovery**: Automatic crash recovery and support for resuming interrupted transfers.
*   **Advanced Configuration**: Set bandwidth limits, configure retry attempts, and manage application settings.
*   **Persistent & Reliable**: Job and settings configurations are stored in simple YAML files.

## Installation

### Prerequisites

*   Python 3.9+
*   `rsync` (usually pre-installed on macOS/Linux)
*   `rclone` (optional, for cloud storage)

### Setup

```bash
# 1. Clone the project
cd ~/backup-manager

# 2. Create a virtual environment
uv venv

# 3. Install dependencies
uv pip install -r requirements-flask.txt

# 4. Install rclone (if using cloud storage)
brew install rclone

# 5. Configure rclone for your cloud providers
rclone config
```

## Quick Start

### 1. Launch the App

```bash
# Run the Flask application
flask run --port=5001
```

The app will be available at **http://localhost:5001**

### 2. Create and Run a Job

1.  Navigate to the **Jobs** page.
2.  Click **"➕ New Job"** and fill in the source, destination, and other details.
3.  Find your new job in the list and click **"▶️ Start"**.
4.  Monitor the progress on the **Dashboard**.

## Project Structure

```
backup-manager/
├── flask_app.py            # Main application entry point
├── flask_app/              # The Flask application package
│   ├── __init__.py         # Application factory (create_app)
│   ├── routes/             # Application pages (Blueprints)
│   ├── services/           # Business logic layer
│   ├── static/             # CSS, JS, and image assets
│   └── templates/          # HTML templates
├── core/                   # Core application logic (JobManager, Settings)
├── engines/                # Backup engines (rsync, rclone)
├── storage/                # YAML storage handling
├── jobs.yaml               # Job configurations (created at runtime)
└── settings.yaml           # User settings (created at runtime)
```

## Testing

To run the test suite, see the instructions in `TESTING.md`.

```bash
# See TESTING.md for detailed test scenarios
cat TESTING.md
```

## Troubleshooting

*   **Job Won't Start**: Check the "Logs" page for errors. Verify that the source and destination paths exist and that you have the correct permissions.
*   **Transfer Fails**: Check your network connectivity. For `rclone` jobs, ensure your remote is configured correctly by running `rclone listremotes`.
*   **App Crashed During Transfer**: Restart the app. A recovery prompt will appear in the sidebar, allowing you to safely mark the interrupted jobs as "paused" so you can resume them manually.

## Credits

*   **Backend**: [Flask](https://flask.palletsprojects.com/), [Flask-SocketIO](https://flask-socketio.readthedocs.io/)
*   **Sync Tools**: [rsync](https://rsync.samba.org/), [rclone](https://rclone.org/)
*   **Configuration**: [PyYAML](https://pyyaml.org/)

---
