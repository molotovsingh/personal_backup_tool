# rclone-remote-cleanup Specification

## Purpose
TBD - created by archiving change harden-rclone-workflow. Update Purpose after archive.
## Requirements
### Requirement: Remote source deletion SHALL remove empty directories

After successfully deleting files from a remote source, the engine MUST invoke `rclone rmdirs` to remove empty directory trees.

#### Scenario: Remote deletion cleans up empty directories

**Given** a job with remote source (e.g., `gdrive:Photos`)
**And** `delete_source_after=True`
**And** `deletion_mode='verify_then_delete'`
**When** verification passes
**And** `rclone delete <source>` completes successfully
**Then** the engine SHALL invoke `rclone rmdirs <source>`
**And** the engine SHALL log "Removing empty directories from remote..."
**And** if rmdirs succeeds, log "✅ Empty directories removed"
**And** if rmdirs fails, log the error but do NOT fail the entire job

#### Scenario: Local deletion skips rmdirs

**Given** a job with local source (e.g., `/Users/me/Photos`)
**And** `delete_source_after=True`
**When** deletion completes
**Then** empty directory removal is handled by normal file system deletion
**And** `rclone rmdirs` SHALL NOT be invoked

#### Scenario: Rmdirs failure does not fail job

**Given** a job with remote source
**And** file deletion succeeded
**When** `rclone rmdirs` is invoked
**And** rmdirs returns non-zero exit code
**Then** the error SHALL be logged
**And** the job status SHALL remain "completed" (not failed)
**And** deletion phase SHALL complete normally

