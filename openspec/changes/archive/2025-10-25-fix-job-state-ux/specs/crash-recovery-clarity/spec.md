# Spec: Crash Recovery Action Clarity

## ADDED Requirements

### Requirement: Crash recovery prompt actions accurately describe their behavior

The crash recovery prompt SHALL accurately describe what each action does when jobs are interrupted (status=running when app loads). Actions MUST NOT use misleading terminology that violates user expectations.

**Current behavior** (problematic):
- "Resume Interrupted Jobs" button marks jobs as paused (does NOT start them)
- "Ignore" button also marks jobs as paused (same side effect, not a true dismiss)
- Both actions modify job state but with unclear/misleading labels

**Required behavior**:
- Primary action labeled "Recover (mark as paused)" with help text explaining it ensures safe state
- Secondary action labeled "Dismiss" that truly dismisses without modifying any job statuses
- Clear messaging about what happened after each action

#### Scenario: User clicks primary recovery action

**Given** the app has detected 2 interrupted jobs (status=running)
**When** the user clicks "Recover (mark as paused)" in the sidebar prompt
**Then** both jobs are marked as paused in storage
**And** a success message displays: "✓ Marked 2 job(s) as paused. You can restart them manually."
**And** the recovery prompt is hidden
**And** the user can later manually start the paused jobs

#### Scenario: User clicks dismiss action

**Given** the app has detected 2 interrupted jobs (status=running)
**When** the user clicks "Dismiss" in the sidebar prompt
**Then** no job statuses are modified (jobs remain in their current state)
**And** the recovery prompt is hidden
**And** the user is responsible for handling the interrupted jobs manually

#### Scenario: Recovery button shows help text

**Given** the crash recovery prompt is visible
**When** the user hovers over "Recover (mark as paused)" button
**Then** help text displays: "Ensures safe state; you can resume manually."

### Requirement: Recovery prompt header remains informative

The recovery prompt header SHALL clearly indicate the number of interrupted jobs and the situation without causing excessive alarm.

#### Scenario: Recovery prompt header displays count

**Given** the app detects 3 interrupted jobs
**When** the recovery prompt is shown
**Then** the header displays: "⚠️ 3 interrupted job(s) found"
**And** uses warning styling (not error) to indicate actionable state
