# rclone-retry-correctness Specification

## Purpose
TBD - created by archiving change harden-rclone-workflow. Update Purpose after archive.
## Requirements
### Requirement: Rclone retry SHALL preserve per-file deletion operation type

When a per-file deletion job (`deletion_mode='per_file'`) encounters a network error and retries, the retry MUST use `rclone move` instead of falling back to `rclone copy`.

#### Scenario: Per-file move job retries with move operation

**Given** a job with `delete_source_after=True` and `deletion_mode='per_file'`
**And** the initial transfer started with `rclone move`
**When** a network error occurs during transfer
**And** the engine invokes `_restart_process()` for retry
**Then** the retry command SHALL use `rclone move` (not `rclone copy`)
**And** the command SHALL include `--delete-empty-src-dirs` flag
**And** source files SHALL continue to be deleted as they are transferred

#### Scenario: Copy-then-delete job retries with copy operation

**Given** a job with `delete_source_after=True` and `deletion_mode='verify_then_delete'`
**And** the initial transfer started with `rclone copy`
**When** a network error occurs during transfer
**And** the engine invokes `_restart_process()` for retry
**Then** the retry command SHALL use `rclone copy`
**And** source files SHALL NOT be deleted until verification passes

#### Scenario: No-deletion job retries with copy operation

**Given** a job with `delete_source_after=False`
**And** the initial transfer started with `rclone copy`
**When** a network error occurs during transfer
**And** the engine invokes `_restart_process()` for retry
**Then** the retry command SHALL use `rclone copy`
**And** source files SHALL remain untouched

