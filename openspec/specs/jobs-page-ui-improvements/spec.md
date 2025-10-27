# jobs-page-ui-improvements Specification

## Purpose
TBD - created by archiving change improve-jobs-ui-collapsible-inline. Update Purpose after archive.
## Requirements
### Requirement: Create job form displays inline without modal overlay

The jobs page SHALL provide an inline expandable form to create new backup jobs without hiding existing jobs.

#### Scenario: Inline form expands and collapses

**Given** the user is on the jobs page
**When** the user clicks the "+ Create New Job" button
**Then** the create form expands inline at the top of the page
**And** the button text changes to "− Cancel"
**And** the expansion uses a smooth slide-down animation
**And** existing jobs remain visible below the form
**And** no modal overlay is displayed

**Given** the create form is expanded
**When** the user clicks the "− Cancel" button
**Then** the form collapses with a slide-up animation
**And** the button text changes back to "+ Create New Job"
**And** form fields are reset to empty

#### Scenario: Form submission collapses form automatically

**Given** the create form is expanded and filled out
**When** the user submits the form successfully
**Then** the job is created via HTMX
**And** the form automatically collapses
**And** form fields are reset to empty
**And** the new job appears in the job list below

### Requirement: Job cards support collapse and expand with smart defaults

Job cards SHALL be collapsible to reduce vertical space while keeping important jobs (running) visible by default.

#### Scenario: Collapsed job card shows essential information

**Given** a job card is in collapsed state
**When** the card is displayed
**Then** the card shows only one line with: expand arrow, name, status badge, action buttons
**And** if the job is running, a mini inline progress bar is shown (20px wide, 2px tall)
**And** if the job is not running, no progress information is shown
**And** source/destination paths are hidden
**And** detailed settings are hidden

#### Scenario: Expanded job card shows full details

**Given** a job card is in expanded state
**When** the card is displayed
**Then** the expand arrow points down (▼)
**And** job type badge (rsync/rclone) is shown
**And** source and destination paths are shown
**And** if job has progress, full progress bar with percentage is shown
**And** if job is running, transfer stats (speed, ETA) are shown
**And** job settings (bandwidth, created date) are shown
**And** deletion settings are shown if enabled

#### Scenario: User can toggle collapse/expand

**Given** a job card is displayed
**When** the user clicks anywhere on the card
**Then** the card toggles between collapsed and expanded states
**And** the transition uses a smooth animation (150-200ms)
**And** the user's choice is saved to localStorage with key `job_{id}_expanded`

**Given** the user has manually expanded or collapsed a job
**When** the page reloads
**Then** the job card restores the user's preference from localStorage

#### Scenario: Smart auto-expansion on page load

**Given** the jobs page loads with multiple jobs
**When** the page renders
**Then** all jobs with status "running" are automatically expanded
**And** the first non-running job (by list order) is expanded
**And** all other jobs are collapsed
**And** if user has manual preferences in localStorage, those override the defaults

### Requirement: Collapsible UI preserves real-time updates

WebSocket and HTMX updates SHALL work correctly with both collapsed and expanded job cards.

#### Scenario: WebSocket updates progress in collapsed running job

**Given** a running job is displayed in collapsed state
**When** WebSocket emits a progress update
**Then** the mini inline progress bar width is updated
**And** the percentage text next to the progress bar is updated
**And** the card remains in collapsed state
**And** no full card re-render occurs

#### Scenario: WebSocket updates progress in expanded running job

**Given** a running job is displayed in expanded state
**When** WebSocket emits a progress update
**Then** the full progress bar is updated
**And** speed and ETA text are updated
**And** bytes transferred / total bytes are updated
**And** the card remains in expanded state

### Requirement: Alpine.js provides reactive state management

The jobs page SHALL use Alpine.js for managing create form and job card expand/collapse state.

#### Scenario: Alpine.js loads from CDN

**Given** the base template is rendered
**When** the page HTML is sent to the browser
**Then** Alpine.js 3.x is loaded from `cdn.jsdelivr.net` with `defer` attribute
**And** Alpine.js initializes before the page is interactive
**And** all `x-data`, `x-show`, `@click` directives are functional

#### Scenario: Create form state is managed by Alpine.js

**Given** the jobs page uses Alpine.js
**When** the page loads
**Then** the jobs page root element has `x-data="{ createFormOpen: false }"`
**And** the create form has `x-show="createFormOpen"` directive
**And** the button has `@click="createFormOpen = !createFormOpen"` directive
**And** form visibility is controlled purely by Alpine.js reactive state

#### Scenario: Job card collapse state is managed by Alpine.js

**Given** each job card uses Alpine.js
**When** the card is rendered
**Then** the card has `x-data` with `expanded` state initialized from localStorage or smart defaults
**And** the card has `@click="toggle()"` directive to toggle state
**And** the expanded details section has `x-show="expanded"` directive
**And** state changes trigger smooth CSS transitions

