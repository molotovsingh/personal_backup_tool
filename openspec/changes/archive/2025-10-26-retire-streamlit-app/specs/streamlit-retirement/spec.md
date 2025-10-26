# streamlit-retirement Specification

## Purpose

Ensures legacy Streamlit UI is properly archived and all user-facing references direct users to the Flask application. This specification defines requirements for cleanly retiring the Streamlit codebase while preserving restoration capability.

## ADDED Requirements

### Requirement: Streamlit files SHALL be archived with restoration instructions

When Streamlit is retired, the original application files MUST be preserved in an archive directory with clear documentation for restoration if needed.

#### Scenario: Streamlit application files moved to archive

**Given** the original Streamlit application exists at `app.py` and `app.py.bak`
**When** the retirement process is executed
**Then** both files SHALL be moved to `archive/streamlit/`
**And** a README SHALL be created at `archive/streamlit/README.md`
**And** the README SHALL document:
- Archive date and reason
- File listing
- Restoration instructions (how to restore Streamlit)
- Reference to Flask migration documentation

#### Scenario: Archive README provides restoration path

**Given** `archive/streamlit/README.md` exists
**When** a user opens the README
**Then** they SHALL find instructions to copy files back to root
**And** instructions to install Streamlit dependencies
**And** the command to run Streamlit: `uv run streamlit run app.py`

### Requirement: Invoking app.py SHALL provide clear migration guidance

After retirement, users attempting to run the old Streamlit entry point MUST receive helpful instructions to use Flask instead.

#### Scenario: Running app.py shows Flask migration message

**Given** Streamlit has been retired
**And** a stub `app.py` exists in the root directory
**When** the user runs `python app.py` or `uv run streamlit run app.py`
**Then** a clear message SHALL be printed explaining Streamlit retirement
**And** the message SHALL include the Flask start command: `uv run python flask_app.py`
**And** the message SHALL reference documentation: `FLASK_MIGRATION_COMPLETE.md`, `README.md`
**And** the message SHALL mention archive location: `archive/streamlit/app.py`
**And** the script SHALL exit with code 1

#### Scenario: Stub prevents accidental Streamlit usage

**Given** the stub `app.py` exists
**When** the user attempts to start Streamlit
**Then** the app SHALL NOT start
**And** the user SHALL see immediate feedback directing them to Flask
**And** no Streamlit UI SHALL appear

### Requirement: Documentation SHALL reference Flask exclusively

All user-facing documentation, scripts, and installation instructions MUST direct users to the Flask application, with no active references to Streamlit commands.

#### Scenario: Installation script prints Flask start command

**Given** the installation is complete
**When** `install.sh` finishes successfully
**Then** the printed start command SHALL be `uv run python flask_app.py`
**And** no Streamlit commands SHALL be printed

#### Scenario: Testing documentation uses Flask commands

**Given** `TESTING.md` contains startup instructions
**When** the user follows testing procedures
**Then** all commands SHALL reference Flask: `uv run python flask_app.py`
**And** no commands SHALL reference Streamlit: `streamlit run app.py`

#### Scenario: Setup script prints Flask guidance

**Given** `setup_jobs.py` completes successfully
**When** the script prints usage instructions
**Then** the printed command SHALL be `uv run python flask_app.py`
**And** no Streamlit commands SHALL be printed

#### Scenario: Requirements file contains no Streamlit dependencies

**Given** `requirements.txt` is the dependency manifest
**When** searching for Streamlit references
**Then** no Streamlit package names SHALL appear (not even in comments)
**And** all Flask dependencies SHALL remain intact

### Requirement: Flask application SHALL remain fully functional after retirement

Retiring Streamlit MUST NOT affect Flask application functionality, as both UIs share business logic and storage.

#### Scenario: Flask app starts successfully after retirement

**Given** Streamlit has been retired
**When** the user runs `uv run python flask_app.py`
**Then** Flask SHALL start on port 5001
**And** the dashboard SHALL load at http://localhost:5001
**And** all pages (Jobs, Settings, Logs) SHALL be accessible
**And** all job operations (create, start, pause, delete) SHALL work

#### Scenario: Existing jobs and settings remain accessible

**Given** jobs exist in `jobs.yaml` from before retirement
**And** settings exist in `settings.yaml`
**When** the user opens the Flask UI
**Then** all jobs SHALL be visible and operable
**And** all settings SHALL be preserved
**And** no data migration is required (shared YAML storage)
