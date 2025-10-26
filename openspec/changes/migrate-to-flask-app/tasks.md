# Tasks: Migrate to Flask Application

## Implementation Order

Tasks are ordered to deliver incremental value, starting with infrastructure and moving to user-facing features. Each task is independently testable.

---

### Phase 1: Infrastructure Setup

#### 1. Create Flask app directory structure
**Capability**: flask-application-structure
**Duration**: 1-2 hours
**Changes**:
- Create `flask_app/` directory with subdirectories: routes/, templates/, static/, utils/
- Create `flask_app/__init__.py` with app factory pattern
- Create `flask_app/config.py` for configuration management
- Create `flask_app.py` as entry point

**Verification**:
- Run `python flask_app.py` → Flask starts on port 5000
- Navigate to http://localhost:5000/ → See "Flask app running" placeholder
- No errors in console

**Dependencies**: None
**Parallelizable**: Yes (can be done independently)

---

#### 2. Install and configure dependencies
**Capability**: flask-application-structure
**Duration**: 30 minutes
**Changes**:
- Add to requirements.txt: Flask, Flask-SocketIO, python-socketio, Flask-Session
- Install Tailwind CSS CLI
- Create `package.json` for Tailwind (if needed) or use standalone CLI
- Configure Tailwind CSS with `tailwind.config.js`
- Create `flask_app/static/css/input.css` with Tailwind directives

**Verification**:
- Run `pip install -r requirements.txt` → All Flask deps installed
- Run `tailwindcss -i flask_app/static/css/input.css -o flask_app/static/css/output.css` → CSS generated
- output.css contains Tailwind classes

**Dependencies**: Task 1 (directory structure)
**Parallelizable**: No (needs directory structure)

---

#### 3. Create base template with navigation
**Capability**: flask-application-structure
**Duration**: 2-3 hours
**Changes**:
- Create `templates/base.html` with: HTML5 boilerplate, Tailwind CSS link, navigation sidebar, main content area
- Add navigation links: Dashboard, Jobs, Settings, Logs
- Style with Tailwind classes (modern, responsive design)
- Include HTMX library via CDN
- Include Socket.IO client library via CDN

**Verification**:
- View base template → Navigation sidebar visible
- Click navigation links → Routes exist (even if empty)
- Responsive: Resize window → Navigation collapses on mobile
- Tailwind classes apply correctly

**Dependencies**: Task 2 (dependencies)
**Parallelizable**: No

---

#### 4. Set up Flask-SocketIO for WebSockets
**Capability**: real-time-updates
**Duration**: 1-2 hours
**Changes**:
- Initialize SocketIO in app factory
- Create `flask_app/socketio_handlers.py` with event handlers
- Implement: connect, disconnect, subscribe_to_job events
- Add reconnection logic in JavaScript

**Verification**:
- Open browser console → See "Connected to Socket.IO"
- Close server → See reconnection attempts in console
- Restart server → Client reconnects automatically

**Dependencies**: Task 1, 2
**Parallelizable**: Yes (can be done in parallel with Task 3)

---

### Phase 2: Settings Page (Simplest)

#### 5. Implement Settings page routes and template
**Capability**: settings-page
**Duration**: 2-3 hours
**Changes**:
- Create `routes/settings.py` blueprint
- Implement GET `/settings` → Display settings form
- Implement POST `/settings/save` → Update settings.yaml
- Implement POST `/settings/reset` → Reset to defaults
- Create `templates/settings.html` extending base.html
- Form fields for: bandwidth limit, auto-start, intervals, retry attempts
- System info section: paths, tool check

**Verification**:
- Navigate to /settings → Form displays with current values
- Change value, click Save → settings.yaml updated
- Click Reset → Values return to defaults
- Tool check shows rsync/rclone status

**Dependencies**: Task 3 (base template)
**Parallelizable**: Yes (independent from other pages)

---

### Phase 3: Logs Page (Read-only)

#### 6. Implement Logs page routes and template
**Capability**: logs-page
**Duration**: 3-4 hours
**Changes**:
- Create `routes/logs.py` blueprint
- Implement GET `/logs` with query params: job_id, search
- Read log files from disk
- Filter and search logic
- Implement GET `/logs/export` → Download text file
- Create `templates/logs.html` extending base.html
- HTMX attributes for: filter dropdown, search input (debounced), refresh button
- Export button

**Verification**:
- Navigate to /logs → All logs displayed
- Select job filter → Only that job's logs shown
- Enter search term → Matching logs highlighted
- Click Export → File downloads with correct content
- Click Refresh → Logs reload

**Dependencies**: Task 3 (base template)
**Parallelizable**: Yes (independent from other pages)

---

### Phase 4: Dashboard Page (Read + Real-time)

#### 7. Implement Dashboard page routes and template
**Capability**: dashboard-page
**Duration**: 4-5 hours
**Changes**:
- Create `routes/dashboard.py` blueprint
- Implement GET `/` → Display dashboard
- Implement GET `/api/dashboard/stats` → Return stats HTML fragment (for HTMX)
- Calculate stats: active jobs count, total bytes, network status
- Create `templates/dashboard.html` extending base.html
- Active jobs panel with progress bars
- Recent activity feed
- HTMX polling attribute: `hx-get="/api/dashboard/stats" hx-trigger="every 2s"`

**Verification**:
- Navigate to / → Dashboard displays stats
- Start a job (via Streamlit) → Dashboard shows active job
- Watch for 5 seconds → Stats auto-refresh without page reload
- Check browser network tab → HTMX polling requests visible

**Dependencies**: Task 3 (base template), Task 4 (WebSockets optional)
**Parallelizable**: Partially (can start without WebSockets)

---

#### 8. Add WebSocket updates to Dashboard
**Capability**: real-time-updates
**Duration**: 2-3 hours
**Changes**:
- Emit job_progress events from Flask-SocketIO when job updates
- JavaScript listener for job_progress events
- Update active jobs panel dynamically
- Emit job_status_change events when status changes
- Update recent activity feed dynamically

**Verification**:
- Start job → Dashboard immediately shows progress
- Job progresses → Progress bar updates smoothly (no polling delay)
- Job completes → Status updates immediately, recent activity updated
- Browser console → See WebSocket messages

**Dependencies**: Task 4 (WebSockets), Task 7 (Dashboard page)
**Parallelizable**: No

---

### Phase 5: Jobs Page (Complex CRUD + Real-time)

#### 9. Implement Jobs page routes (list, delete)
**Capability**: jobs-page
**Duration**: 3-4 hours
**Changes**:
- Create `routes/jobs.py` blueprint
- Implement GET `/jobs` → Display all jobs
- Implement DELETE `/jobs/{id}` → Delete job (HTMX)
- Create `templates/jobs.html` extending base.html
- Job list with cards
- Status badges (color-coded)
- Delete button with confirmation modal (HTML dialog)

**Verification**:
- Navigate to /jobs → All jobs listed
- Job cards show name, type, source, dest, status
- Click Delete → Confirmation modal appears
- Confirm delete → Job removed from list (no page reload)

**Dependencies**: Task 3 (base template)
**Parallelizable**: No (foundational for remaining jobs tasks)

---

#### 10. Implement create job form
**Capability**: jobs-page
**Duration**: 3-4 hours
**Changes**:
- Implement GET `/jobs/new` → Display create form
- Implement POST `/jobs` → Create job with validation
- Form fields: name, type, source, dest, bandwidth, deletion settings
- Path validation (source exists, dest writable)
- HTMX form submission (inline errors)

**Verification**:
- Click "New Job" → Form displays
- Submit invalid form → Inline errors shown
- Submit valid form → Job created, added to list
- Form clears after successful creation

**Dependencies**: Task 9 (Jobs list)
**Parallelizable**: No

---

#### 11. Implement start/pause job controls
**Capability**: jobs-page
**Duration**: 2-3 hours
**Changes**:
- Implement POST `/jobs/{id}/start` → Start job (HTMX)
- Implement POST `/jobs/{id}/pause` → Pause job (HTMX)
- Return updated job card HTML fragment
- Button visibility logic: pending/paused → Start, running → Pause, completed → none

**Verification**:
- Click Start on pending job → Job starts, button changes to Pause
- Click Pause on running job → Job pauses, button changes to Resume
- Completed job → No action buttons shown

**Dependencies**: Task 9 (Jobs list)
**Parallelizable**: Partially (can work in parallel with Task 10)

---

#### 12. Add real-time progress to Jobs page
**Capability**: real-time-updates, jobs-page
**Duration**: 2-3 hours
**Changes**:
- WebSocket emits from job engine progress callbacks
- JavaScript listener for job_progress events on Jobs page
- Update progress bars, speed, ETA dynamically
- Update status badges when job completes/fails

**Verification**:
- Start job → Progress bar appears and updates smoothly
- Speed and ETA update in real-time
- Job completes → Status badge changes to "Completed"
- No HTMX polling needed (WebSocket handles updates)

**Dependencies**: Task 4 (WebSockets), Task 11 (start/pause)
**Parallelizable**: No

---

### Phase 6: Crash Recovery

#### 13. Implement crash recovery prompt
**Capability**: jobs-page
**Duration**: 2 hours
**Changes**:
- Check for interrupted jobs on Flask app startup (status=running)
- Store interrupted jobs in session
- Display recovery prompt in navigation sidebar (similar to Streamlit)
- Buttons: "Recover (mark as paused)" and "Dismiss"
- HTMX handling for button clicks

**Verification**:
- Set job status to running in jobs.yaml
- Restart Flask app
- Navigate to any page → See recovery prompt in sidebar
- Click "Recover" → Jobs marked as paused, prompt disappears
- Reset, click "Dismiss" → Prompt disappears, jobs unchanged

**Dependencies**: Task 3 (base template), Task 11 (start/pause logic)
**Parallelizable**: No

---

### Phase 7: Polish & Testing

#### 14. Responsive design and mobile testing
**Capability**: All pages
**Duration**: 2-3 hours
**Changes**:
- Test all pages on mobile viewport (375px, 768px, 1024px)
- Adjust Tailwind classes for responsive breakpoints
- Ensure navigation collapses on mobile (hamburger menu)
- Test touch interactions (buttons, forms)

**Verification**:
- Resize browser to mobile sizes → Layout adjusts properly
- Navigation → Responsive on all screen sizes
- Forms → Usable on mobile (appropriate input sizes)
- No horizontal scroll on mobile

**Dependencies**: All pages implemented
**Parallelizable**: No (needs all pages done)

---

#### 15. Error handling and edge cases
**Capability**: flask-application-structure
**Duration**: 2-3 hours
**Changes**:
- Custom 404 page with navigation
- Custom 500 page with error logging
- Handle WebSocket disconnection gracefully
- Handle HTMX request failures (show toast/alert)
- Validate all user inputs

**Verification**:
- Navigate to /nonexistent → 404 page shown
- Trigger server error → 500 page shown, logged
- Disconnect network → Reconnection indicator shown
- Submit invalid form → Errors displayed

**Dependencies**: All pages implemented
**Parallelizable**: Partially (can test 404/500 early)

---

#### 16. Performance testing and optimization
**Capability**: All
**Duration**: 2-3 hours
**Changes**:
- Benchmark page load times (< 500ms target)
- Benchmark HTMX response times (< 200ms target)
- Profile WebSocket latency (< 100ms target)
- Optimize Tailwind CSS (purge unused classes)
- Add caching headers for static assets

**Verification**:
- Page load < 500ms (measured)
- Job start response < 200ms
- WebSocket updates < 100ms latency
- output.css file size reasonable (~10-20KB gzipped)

**Dependencies**: All features implemented
**Parallelizable**: No

---

#### 17. Migration guide and documentation
**Capability**: N/A (documentation)
**Duration**: 2-3 hours
**Changes**:
- Create FLASK_MIGRATION.md with: setup instructions, how to run Flask app, feature comparison, troubleshooting
- Update README.md with Flask option
- Document deployment (Gunicorn + Nginx example)
- Document how to switch from Streamlit to Flask

**Verification**:
- Follow migration guide → Flask app runs
- All steps documented clearly
- Troubleshooting section covers common issues

**Dependencies**: All tasks complete
**Parallelizable**: Yes (can write docs while coding)

---

## Testing Checklist

After all tasks, verify feature parity:

### Dashboard
- [ ] Shows active job count, total bytes, network status
- [ ] Auto-refreshes stats every 2 seconds
- [ ] Displays active jobs panel with progress
- [ ] Shows recent activity feed (last 10 events)

### Jobs
- [ ] Lists all jobs with status badges
- [ ] Create job form with validation
- [ ] Start/pause/delete job via HTMX
- [ ] Real-time progress updates via WebSocket
- [ ] Crash recovery prompt works

### Settings
- [ ] Form displays all settings
- [ ] Save settings updates YAML file
- [ ] Reset to defaults works
- [ ] System info displays paths and tool status

### Logs
- [ ] Displays all logs
- [ ] Filter by job works
- [ ] Search logs works (debounced)
- [ ] Export logs downloads file
- [ ] Manual refresh works

### General
- [ ] Responsive design on all screen sizes
- [ ] Error pages (404, 500) display correctly
- [ ] No regressions in existing features
- [ ] Performance meets targets

## Rollback Plan

If issues arise:
1. Streamlit app continues to run on port 8501 (unchanged)
2. Users can switch back by using http://localhost:8501
3. No data migrations occurred (both use same YAML files)
4. Flask app can be removed without affecting Streamlit

## Estimated Timeline

- **Phase 1 (Infrastructure)**: 1-2 days
- **Phase 2 (Settings)**: 0.5 day
- **Phase 3 (Logs)**: 0.5-1 day
- **Phase 4 (Dashboard)**: 1-1.5 days
- **Phase 5 (Jobs)**: 2-3 days
- **Phase 6 (Crash Recovery)**: 0.5 day
- **Phase 7 (Polish & Testing)**: 1-2 days

**Total**: ~7-11 days (1.5-2 weeks for single developer)
