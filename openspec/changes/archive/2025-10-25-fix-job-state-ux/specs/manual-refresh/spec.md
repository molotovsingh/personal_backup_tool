# Spec: Manual Refresh for Jobs Page

## ADDED Requirements

### Requirement: Jobs page provides manual refresh when auto-refresh is inactive

The Jobs page SHALL provide a manual refresh control when auto-refresh is inactive (no jobs running). Users MUST be able to refresh page state without navigating away and back.

**Current behavior** (limitation):
- Auto-refresh gated by "has running jobs" check (app.py:372)
- When all jobs idle, no refresh affordance exists
- Users must navigate to different page and back to refresh

**Required behavior**:
- Manual refresh control visible when auto-refresh is inactive
- Clicking refresh triggers immediate page re-render
- Positioned near page header for easy access

#### Scenario: Manual refresh button appears when no jobs running

**Given** all jobs have status "pending", "paused", "completed", or "failed"
**And** no jobs have status "running"
**When** the Jobs page is rendered
**Then** a "🔄 Refresh" button is visible near the page header
**And** the auto-refresh LIVE indicator is not shown
**And** no automatic refresh occurs

#### Scenario: Manual refresh button triggers re-render

**Given** the manual "🔄 Refresh" button is visible
**When** the user clicks the button
**Then** the page immediately re-renders
**And** all job states are reloaded from storage
**And** the updated states are displayed

#### Scenario: Manual refresh button hidden when jobs are running

**Given** at least one job has status "running"
**When** the Jobs page is rendered
**Then** no manual "🔄 Refresh" button is visible
**And** the "🔴 LIVE" indicator is shown
**And** auto-refresh runs every N seconds (from settings)
**And** users rely on auto-refresh for updates

#### Scenario: Refresh button is compact and non-intrusive

**Given** the manual refresh button is visible
**When** rendered on the page
**Then** it appears as a compact control (not full-width)
**And** positioned near the "Backup Jobs" header
**And** uses icon + text for clarity
**And** does not dominate the page layout
