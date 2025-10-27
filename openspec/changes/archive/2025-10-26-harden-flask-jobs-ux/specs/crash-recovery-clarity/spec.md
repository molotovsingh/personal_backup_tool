# Crash Recovery Clarity

**ID**: `crash-recovery-clarity`
**Created**: 2025-10-26
**Updated**: 2025-10-26

## Overview

The crash recovery prompt appears when interrupted jobs are detected on Flask app startup. This spec ensures the prompt provides clear guidance and prevents double-submit issues.

## ADDED Requirements

### Requirement: Clear recovery action guidance

**ID**: `REQ-crash-recovery-001`

The "Recover" button MUST include helper text explaining what happens when clicked, and both buttons MUST prevent double-submit.

**Why**: Users need to understand the recovery action (marks jobs as paused, safe to resume later) and accidental double-clicks should be prevented.

**Acceptance Criteria**:
- Helper text under "Recover" button explains action
- Helper text visible and readable (color contrast passes WCAG AA)
- Recover button disables immediately on click
- Dismiss button disables immediately on click
- Form submits only once per button click
- Buttons remain disabled after form submission

#### Scenario: Helper text is visible and readable

**Given** crash recovery prompt is displayed
**When** user views the prompt
**Then** helper text appears under "Recover (mark as paused)" button
**And** helper text reads "Ensures safe state; resume later from Jobs."
**And** text color contrast passes WCAG AA standards

#### Scenario: Recover button prevents double-submit

**Given** crash recovery prompt is displayed
**When** user clicks "Recover" button twice rapidly
**Then** button disables immediately on first click
**And** only one POST request to /recover-jobs is sent
**And** button remains disabled after form submission

#### Scenario: Dismiss button prevents double-submit

**Given** crash recovery prompt is displayed
**When** user clicks "Dismiss" button twice rapidly
**Then** button disables immediately on first click
**And** only one POST request to /dismiss-recovery is sent
**And** button remains disabled after form submission

#### Scenario: Disabled state is visually clear

**Given** crash recovery prompt is displayed
**When** user clicks any button
**Then** button shows disabled state (reduced opacity or cursor:not-allowed)
**And** visual feedback is immediate (no delay)

### Requirement: Prompt rendering correctness

**ID**: `REQ-crash-recovery-002`

Crash recovery prompt MUST render only when interrupted jobs exist and MUST display accurate job count.

**Why**: Prevents unnecessary prompts and ensures users have correct information about interrupted jobs.

**Acceptance Criteria**:
- Prompt appears only when `show_recovery_prompt` is true
- Job count in prompt matches actual interrupted job count
- Prompt disappears after recovery or dismiss action
- No prompt shown on normal app startup (no interrupted jobs)

#### Scenario: No prompt on normal startup

**Given** Flask app starts normally
**And** no jobs were running when app stopped
**When** user opens dashboard
**Then** crash recovery prompt does not appear
**And** page displays normally

#### Scenario: Prompt appears with correct job count

**Given** 2 jobs were running when app crashed
**When** Flask app restarts and user opens dashboard
**Then** crash recovery prompt appears
**And** prompt displays "2 interrupted job(s)"
**And** interrupted job count matches actual count

#### Scenario: Prompt disappears after recovery

**Given** crash recovery prompt is displayed
**When** user clicks "Recover (mark as paused)"
**Then** prompt disappears
**And** interrupted jobs are marked as paused
**And** jobs appear in jobs list with paused status

#### Scenario: Prompt disappears after dismiss

**Given** crash recovery prompt is displayed
**When** user clicks "Dismiss"
**Then** prompt disappears
**And** interrupted jobs remain in their current state
**And** no further action is taken on jobs
