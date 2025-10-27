# data-directory-unification Specification

## Purpose
Unify data storage paths across Flask UI and engine components to ensure logs, jobs, and settings are written to and read from the same location.

## ADDED Requirements

### Requirement: All components SHALL use a unified data directory

The application MUST derive all data paths (logs, jobs, settings) from a single configurable root directory to ensure consistency between engines and Flask UI.

#### Scenario: Data directory defaults to home directory

**Given** the `BACKUP_MANAGER_DATA_DIR` environment variable is NOT set
**When** the application initializes
**Then** the data directory SHALL default to `~/backup-manager`
**And** logs SHALL be written to `~/backup-manager/logs/`
**And** jobs SHALL be stored in `~/backup-manager/jobs/`
**And** settings SHALL be stored in `~/backup-manager/settings/`

#### Scenario: Custom data directory from environment variable

**Given** the `BACKUP_MANAGER_DATA_DIR` environment variable is set to `/var/lib/backup-manager`
**When** the application initializes
**Then** the data directory SHALL be `/var/lib/backup-manager`
**And** logs SHALL be written to `/var/lib/backup-manager/logs/`
**And** jobs SHALL be stored in `/var/lib/backup-manager/jobs/`
**And** settings SHALL be stored in `/var/lib/backup-manager/settings/`

#### Scenario: Rclone engine writes logs to unified directory

**Given** the unified data directory is configured
**When** a rclone job starts
**Then** the engine SHALL write logs to `<data_dir>/logs/rclone_<job_id>.log`
**And** Flask UI SHALL read logs from the same `<data_dir>/logs/` directory
**And** logs SHALL appear in the Flask Logs page

#### Scenario: Rsync engine writes logs to unified directory

**Given** the unified data directory is configured
**When** an rsync job starts
**Then** the engine SHALL write logs to `<data_dir>/logs/rsync_<job_id>.log`
**And** Flask UI SHALL read logs from the same `<data_dir>/logs/` directory
**And** logs SHALL appear in the Flask Logs page

#### Scenario: Job storage uses unified directory

**Given** the unified data directory is configured
**When** a job is created
**Then** job data SHALL be persisted to `<data_dir>/jobs/`
**And** both Flask UI and engines SHALL read/write from the same location
**And** job list SHALL be consistent across all components

### Requirement: Directory structure SHALL be created automatically

The application MUST ensure the data directory and subdirectories exist before use.

#### Scenario: Data directory structure is initialized on startup

**Given** the data directory path is determined (default or from env)
**When** the application starts
**And** the directory does NOT exist
**Then** the application SHALL create the directory
**And** subdirectories `logs/`, `jobs/`, `settings/` SHALL be created
**And** appropriate permissions SHALL be set

#### Scenario: Existing data directory is reused

**Given** the data directory already exists
**And** contains existing logs, jobs, and settings
**When** the application starts
**Then** the existing data SHALL be preserved
**And** the application SHALL continue using the same directory
**And** no data migration is required
