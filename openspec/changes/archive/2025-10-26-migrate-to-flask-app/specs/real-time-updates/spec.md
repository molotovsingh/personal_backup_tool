# Spec: Real-time Updates

## ADDED Requirements

### Requirement: WebSocket connection for job progress updates

The application SHALL establish WebSocket connections using Flask-SocketIO to provide real-time job progress updates without polling.

#### Scenario: WebSocket connection established on page load

**Given** the user opens a page that displays job progress (Dashboard or Jobs)
**When** the page loads
**Then** JavaScript establishes WebSocket connection to Flask-SocketIO
**And** connection event is logged (client and server)
**And** client subscribes to relevant events (progress, status_change)
**And** connection remains open until page is closed

#### Scenario: Job progress emitted via WebSocket

**Given** a job is running
**When** the job makes progress (bytes transferred updated)
**Then** Flask-SocketIO emits 'job_progress' event with:
  - job_id
  - bytes_transferred
  - percent
  - speed_bytes
  - eta_seconds
**And** all connected clients receive the event
**And** updates are sent at most once per second (throttled)

#### Scenario: Job status change emitted via WebSocket

**Given** a job changes status (running → completed, running → failed, etc.)
**When** the status change occurs
**Then** Flask-SocketIO emits 'job_status_change' event with:
  - job_id
  - old_status
  - new_status
  - timestamp
**And** all connected clients receive the event immediately
**And** clients update UI accordingly

#### Scenario: WebSocket reconnection on disconnect

**Given** a WebSocket connection is established
**When** the connection is lost (network issue, server restart)
**Then** Socket.IO client automatically attempts reconnection
**And** exponential backoff is used (1s, 2s, 4s, 8s, max 30s)
**And** user sees a "Reconnecting..." indicator
**And** when reconnected, user sees "Connected" indicator
**And** page state is refreshed after reconnection

### Requirement: HTMX polling for dashboard statistics

The dashboard SHALL use HTMX polling to auto-refresh statistics every N seconds (configurable).

#### Scenario: Dashboard polls for stats updates

**Given** the dashboard page is loaded
**When** the auto-refresh interval elapses (default 2 seconds)
**Then** HTMX sends GET request to `/api/dashboard/stats`
**And** Flask returns HTML fragment with updated statistics
**And** HTMX swaps the statistics section with new content
**And** no full page reload occurs
**And** polling continues indefinitely while page is open

#### Scenario: Dashboard stats polling respects user settings

**Given** the user has configured auto-refresh interval to 5 seconds
**When** the dashboard page loads
**Then** HTMX polls every 5 seconds (not the default 2 seconds)
**And** interval is read from user settings
**And** changes to settings take effect on next page load

### Requirement: Graceful degradation when WebSocket fails

The application SHALL gracefully degrade to HTMX polling if WebSocket connection fails or is not supported.

#### Scenario: Fallback to polling on WebSocket failure

**Given** WebSocket connection cannot be established (firewall, proxy)
**When** the connection attempt fails after retries
**Then** the application switches to HTMX polling mode
**And** job progress is updated via polling `/api/jobs/{id}/progress` every 2 seconds
**And** user sees a notice: "Using polling mode (WebSocket unavailable)"
**And** functionality remains available (slightly higher latency)

#### Scenario: Detect WebSocket support on page load

**Given** the user's browser does not support WebSocket
**When** the page loads
**Then** JavaScript detects lack of WebSocket support
**And** application starts in polling mode immediately
**And** no WebSocket connection is attempted
**And** user experience is identical (just higher latency)
