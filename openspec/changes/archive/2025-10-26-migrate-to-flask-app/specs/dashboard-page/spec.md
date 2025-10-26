# Spec: Dashboard Page

## ADDED Requirements

### Requirement: Dashboard displays real-time job statistics

The dashboard page SHALL display an overview of all jobs with real-time statistics including active job count, total bytes transferred, and network status. Updates MUST occur automatically without full page refreshes.

#### Scenario: Dashboard shows current job statistics

**Given** the user navigates to the dashboard page
**When** the page loads
**Then** the dashboard displays the number of active jobs
**And** displays total bytes transferred across all jobs
**And** displays current network status (online/offline)
**And** displays the last update timestamp

#### Scenario: Dashboard auto-refreshes stats

**Given** the dashboard page is open
**When** 2 seconds pass (configurable refresh interval)
**Then** HTMX polls the stats endpoint `/api/dashboard/stats`
**And** the statistics are updated without full page reload
**And** the update is seamless (no flash/flicker)
**And** the last update timestamp changes

#### Scenario: Dashboard shows active jobs panel

**Given** at least one job is running
**When** the dashboard displays active jobs
**Then** each running job shows: name, progress percentage, speed, ETA
**And** progress bars are visually updated
**And** jobs are sorted by start time (newest first)
**And** maximum 5 active jobs are displayed (expandable)

### Requirement: Dashboard displays recent activity feed

The dashboard SHALL display the last 10 significant events across all jobs (job started, completed, failed, paused).

#### Scenario: Recent activity shows latest events

**Given** jobs have been run recently
**When** the dashboard page loads
**Then** the recent activity feed displays the last 10 events
**And** each event shows: timestamp, job name, event type, status
**And** events are sorted by timestamp (newest first)
**And** event types are color-coded (success=green, failure=red, info=blue)

#### Scenario: Activity feed updates automatically

**Given** a job changes state (starts, completes, fails)
**When** the dashboard auto-refreshes
**Then** the new event appears in the recent activity feed
**And** older events are pushed down
**And** the feed maintains maximum 10 events
