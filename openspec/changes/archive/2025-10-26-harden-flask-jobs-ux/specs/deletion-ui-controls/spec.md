# Deletion UI Controls

**ID**: `deletion-ui-controls`
**Created**: 2025-10-26
**Updated**: 2025-10-26

## Overview

The deletion checkbox and options UI provide controls for configuring source file deletion after successful backups. This spec ensures the controls are robust, accessible, and handle edge cases gracefully.

## ADDED Requirements

### Requirement: Deletion checkbox robustness

**ID**: `REQ-deletion-ui-001`

The deletion checkbox MUST handle rapid toggling, network failures, and provide appropriate feedback without race conditions or stale UI states.

**Why**: Users may rapidly toggle controls or experience network issues. The UI must remain in a consistent, predictable state.

**Acceptance Criteria**:
- Rapid checkbox toggling drops in-flight HTMX requests (no race conditions)
- Loading indicator appears during HTMX requests
- Network errors display user-friendly error messages
- Final UI state always matches checkbox state
- No JavaScript errors in console during interactions

#### Scenario: Rapid checkbox toggling

**Given** the job creation form is open
**When** user toggles deletion checkbox 5-10 times quickly
**Then** loading indicator appears during HTMX requests
**And** in-flight requests are dropped (hx-sync behavior)
**And** final UI state matches checkbox state
**And** no race conditions occur

#### Scenario: Network error handling

**Given** the job creation form is open
**And** network is offline (simulated in DevTools)
**When** user toggles deletion checkbox
**Then** error message appears in deletion-options area
**And** error message reads "Failed to load options. Try again."

#### Scenario: State consistency after rapid toggling

**Given** the job creation form is open
**When** user performs any sequence of checkbox toggles
**Then** deletion options visibility always matches checkbox state
**And** no stale HTMX responses overwrite newer states

### Requirement: Accessibility for deletion controls

**ID**: `REQ-deletion-ui-002`

Deletion checkbox and options MUST follow accessibility best practices with proper ARIA attributes and semantic HTML.

**Why**: Screen reader users need clear announcements about control relationships and dynamic content changes.

**Acceptance Criteria**:
- Checkbox has `aria-controls` pointing to deletion-options container
- Checkbox has `aria-expanded` that updates on toggle
- Deletion options container is an ARIA live region
- Screen readers announce when deletion options appear/disappear
- Keyboard navigation works as expected

#### Scenario: Screen reader announces checkbox control

**Given** screen reader is active (NVDA/JAWS/VoiceOver)
**When** user navigates to deletion checkbox
**Then** screen reader announces "Delete source files after successful backup, checkbox"
**And** screen reader announces "controls deletion options"
**And** screen reader announces expanded/collapsed state

#### Scenario: Live region announces options appearance

**Given** screen reader is active
**And** deletion checkbox is unchecked
**When** user checks deletion checkbox
**Then** screen reader announces deletion options content
**And** announcement includes "Deletion Mode" fieldset

#### Scenario: Keyboard navigation works correctly

**Given** deletion checkbox has focus
**When** user presses Space or Enter
**Then** checkbox toggles state
**And** deletion options appear/disappear accordingly
**And** Tab key moves to next focusable element
