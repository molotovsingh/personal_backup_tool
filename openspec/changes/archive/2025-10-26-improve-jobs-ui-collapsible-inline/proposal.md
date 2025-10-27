# Proposal: Improve Jobs UI with Collapsible Cards and Inline Form

## Why

The current jobs page UX has two significant issues affecting usability:

1. **Modal Popup Disruption**: Creating a new job opens a full-screen modal overlay that completely hides the existing job list. Users lose context and cannot reference existing jobs while creating new ones.

2. **Excessive Vertical Space**: Each job card displays all details (paths, settings, progress) at all times, resulting in massive scrolling for users with many jobs. A list of 10 jobs requires ~250 lines of vertical space.

These issues make the interface feel cluttered and disruptive, especially for users managing multiple backup jobs.

## What Changes

Replace the modal with an inline expandable form and make job cards collapsible with smart defaults.

### 1. Inline Create Form (No Popup)
- Remove the full-screen modal overlay
- Add expandable form section at the top of the jobs page
- Form expands inline with smooth slide-down animation
- Button text toggles: "+ Create New Job" ↔ "− Cancel"
- Users can see existing jobs while filling out the form
- Uses Alpine.js for reactive state management

### 2. Collapsible Job Cards
- **Collapsed view** (default for most jobs):
  - Single line showing: name, status badge, quick action buttons
  - Running jobs show mini inline progress bar when collapsed
- **Expanded view** (click to toggle):
  - Full details: source/dest paths, progress bar, transfer stats, settings
- **Smart auto-expansion logic**:
  - Running jobs: Always expanded (highest priority)
  - Most recent non-running job: Expanded (recent context)
  - All other jobs: Collapsed by default
- **Persistent user preferences**:
  - Uses localStorage to remember which jobs user has manually expanded/collapsed
  - Preferences survive page reloads

### 3. Space Efficiency
- ~90% reduction in vertical space (10 jobs: 15 lines vs 250+ lines)
- Inline form is more compact (2-column grid layout)
- Better information density without sacrificing accessibility

## Impact

### User Benefits
- No more context loss during job creation
- Dramatically reduced scrolling for large job lists
- Focus on what matters (running jobs stay visible)
- Cleaner, less overwhelming interface

### Technical Changes
- Add Alpine.js 3.x CDN (lightweight reactive framework)
- Modify `jobs.html` template to use inline form
- Modify `jobs_list.html` partial to support collapse/expand
- No backend changes required (preserves all HTMX functionality)

## Alternatives Considered

1. **Sidebar slide-in form**: More complex, poor mobile support
2. **Dedicated create page**: Loses context entirely, extra navigation
3. **Accordion for jobs only**: Doesn't solve modal problem

Inline form + collapsible cards is the simplest solution that addresses both issues.

## Dependencies

- Alpine.js 3.x (added via CDN, no build step)
- Existing HTMX and Flask-SocketIO functionality (unchanged)

## Success Criteria

- Create form expands inline without page overlay
- Job cards collapse/expand on click with smooth animation
- Running jobs auto-expand, others default to collapsed
- User expand/collapse preferences persist in localStorage
- All existing functionality (WebSocket updates, HTMX actions) continues working
