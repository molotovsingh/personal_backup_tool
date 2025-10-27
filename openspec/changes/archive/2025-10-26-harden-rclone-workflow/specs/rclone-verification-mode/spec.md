# rclone-verification-mode Specification

## Purpose
Honor the `verification_mode='verify_after'` setting by running post-transfer verification regardless of deletion settings, giving users control over backup integrity checks.

## ADDED Requirements

### Requirement: Verify-after mode SHALL run verification even when deletion is disabled

When `verification_mode` is set to `'verify_after'`, the engine MUST run `rclone check` after successful transfer completion, independent of `delete_source_after` setting.

#### Scenario: Verify-after runs without deletion enabled

**Given** a job with `verification_mode='verify_after'`
**And** `delete_source_after=False`
**When** the transfer completes successfully
**Then** the engine SHALL invoke `rclone check <source> <dest>`
**And** `progress['verification']['passed']` SHALL be set to True or False based on check result
**And** `progress['verification']['files_checked']` SHALL be updated
**And** the job SHALL complete (not proceed to deletion since deletion is disabled)

#### Scenario: Verify-after runs with deletion enabled (verify-then-delete mode)

**Given** a job with `verification_mode='verify_after'`
**And** `delete_source_after=True`
**And** `deletion_mode='verify_then_delete'`
**When** the transfer completes successfully
**Then** the engine SHALL invoke `rclone check`
**And** if verification passes, deletion SHALL proceed
**And** if verification fails, deletion SHALL be skipped
**And** `progress['verification']` fields SHALL be populated

#### Scenario: Verify-after with checksum option

**Given** a job with `verification_mode='verify_after'`
**And** checksum verification is requested
**When** post-transfer verification runs
**Then** `rclone check` SHALL include `--checksum` flag
**And** verification SHALL compare file checksums (not just size/modtime)
**And** `progress['verification']['mismatches']` SHALL reflect checksum failures

#### Scenario: Fast mode skips post-transfer verification

**Given** a job with `verification_mode='fast'`
**And** `delete_source_after=False`
**When** the transfer completes successfully
**Then** post-transfer verification SHALL NOT run
**And** `progress['verification']['passed']` SHALL remain None
**And** the job SHALL complete immediately after transfer

### Requirement: Verification progress SHALL be visible in real-time

Verification progress data MUST be available in the progress dict for WebSocket updates.

#### Scenario: Verification progress updates during check

**Given** verification is running via `rclone check`
**When** the check is in progress
**Then** `progress['verification']['passed']` SHALL be None (pending)
**And** when check completes successfully, `passed` SHALL be True
**And** when check finds mismatches, `passed` SHALL be False
**And** `progress['verification']['files_checked']` SHALL reflect files processed
**And** `progress['verification']['mismatches']` SHALL reflect differences found
