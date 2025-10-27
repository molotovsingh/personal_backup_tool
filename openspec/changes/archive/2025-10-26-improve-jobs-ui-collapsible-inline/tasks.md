# Tasks

## Implementation Tasks

- [x] Add Alpine.js CDN to `flask_app/templates/base.html`
  - **Validation**: Verify script tag loads in browser DevTools Network tab
  - **Dependencies**: None

- [x] Replace modal with inline expandable form in `flask_app/templates/jobs.html`
  - **Validation**: Click button to verify form expands/collapses inline without overlay
  - **Dependencies**: Alpine.js added to base template
  - **Details**:
    - Wrap page in Alpine.js component with `createFormOpen` state
    - Add expandable form section with smooth transitions
    - Use 2-column grid layout for compact display
    - Preserve existing HTMX form submission behavior
    - Clear form and collapse after successful submission

- [x] Implement collapsible job cards in `flask_app/templates/partials/jobs_list.html`
  - **Validation**: Click job card to verify smooth expand/collapse animation
  - **Dependencies**: Alpine.js added to base template
  - **Details**:
    - Add Alpine.js component to each job card with `expanded` state
    - Implement collapsed view (1 line with name, status, actions)
    - Implement expanded view (full details)
    - Add inline mini progress bar for running jobs when collapsed
    - Add smart default expansion logic (running=expanded, first non-running=expanded, rest=collapsed)
    - Store user preferences in localStorage with key `job_{id}_expanded`

- [x] Test create form functionality
  - **Validation**: Create a new job via inline form, verify HTMX submission works
  - **Dependencies**: Inline form implemented

- [x] Test collapsible cards with multiple jobs
  - **Validation**:
    - Verify running jobs auto-expand on page load
    - Verify localStorage persists manual expand/collapse choices across page reloads
    - Verify smooth animations work correctly
  - **Dependencies**: Collapsible cards implemented

- [x] Test WebSocket updates with collapsed cards
  - **Validation**: Start a job and verify progress updates work correctly in both collapsed and expanded states
  - **Dependencies**: All UI changes implemented
  - **Details**: Ensure existing WebSocket JavaScript handlers continue updating progress bars

## Documentation Tasks

- [ ] Update user-facing documentation if jobs page screenshots are included
  - **Details**: Replace screenshots showing modal with new inline form UI

## Optional Enhancements (Future)

- [ ] Add keyboard shortcuts (e.g., 'n' for new job, 'space' to expand/collapse)
- [ ] Add "Expand All" / "Collapse All" toggle button
- [ ] Add search/filter to quickly find jobs in long lists
