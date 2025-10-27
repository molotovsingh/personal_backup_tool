# rclone-preflight-checks Specification

## Purpose
Validate rclone binary availability before starting jobs to provide clear, actionable error messages instead of generic engine failures.

## ADDED Requirements

### Requirement: Job creation SHALL validate rclone availability for rclone jobs

Before creating a rclone engine instance, the system MUST verify that the rclone binary is installed and accessible.

#### Scenario: Rclone job creation succeeds when binary is available

**Given** rclone is installed and accessible in PATH
**When** the user creates a job with `type='rclone'`
**Then** the preflight check SHALL pass
**And** the `RcloneEngine` instance SHALL be created
**And** the job SHALL be added to the job list

#### Scenario: Rclone job creation fails with clear error when binary is missing

**Given** rclone is NOT installed or NOT in PATH
**When** the user attempts to create a job with `type='rclone'`
**Then** the preflight check SHALL fail
**And** an error message SHALL be returned: "rclone not found. Install from https://rclone.org"
**And** the `RcloneEngine` instance SHALL NOT be created
**And** the job SHALL NOT be added to the job list
**And** the user SHALL see the error in the UI

#### Scenario: Rsync jobs are unaffected by rclone preflight

**Given** rclone is NOT installed
**When** the user creates a job with `type='rsync'`
**Then** the rclone preflight check SHALL NOT run
**And** the job creation SHALL succeed (if rsync is available)
