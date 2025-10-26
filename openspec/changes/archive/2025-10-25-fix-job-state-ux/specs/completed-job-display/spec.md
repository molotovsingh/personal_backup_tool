# Spec: Completed Job Card Display

## ADDED Requirements

### Requirement: Completed jobs do not show disabled Start button

When a job reaches completed status, the job card SHALL display a clean, terminal state without disabled action buttons. Disabled buttons MUST NOT be shown as they suggest blocked functionality rather than a terminal state.

**Current behavior** (problematic):
- Completed jobs render a disabled "▶️ Start" button
- Suggests an action exists but is blocked
- Creates visual clutter and user confusion

**Required behavior**:
- No Start or Pause buttons for completed jobs
- Status clearly indicated through badge/chip
- Only relevant actions shown (Delete, View Logs)

#### Scenario: Completed job card shows status badge instead of disabled button

**Given** a job with status "completed"
**When** the job card is rendered on the Jobs page
**Then** no "▶️ Start" button is displayed (enabled or disabled)
**And** no "⏸️ Pause" button is displayed
**And** a status indicator shows "✓ Completed"
**And** "🗑️ Delete" button is available
**And** "📄 View Logs" action is available

#### Scenario: Startable job shows enabled Start button

**Given** a job with status "pending", "paused", or "failed"
**When** the job card is rendered on the Jobs page
**Then** an enabled "▶️ Start" button is displayed
**And** clicking it starts the job
**And** no disabled buttons are shown

#### Scenario: Running job shows Pause button instead of Start

**Given** a job with status "running"
**When** the job card is rendered on the Jobs page
**Then** no "▶️ Start" button is displayed
**And** an enabled "⏸️ Pause" button is displayed
**And** clicking it pauses the job
