# Design: Flask Migration Architecture

## Context
Current Streamlit app (1320 lines, app.py) provides backup management UI with 4 pages (Dashboard, Jobs, Settings, Logs). Business logic already separated into core/, engines/, storage/, models/, utils/. Need to migrate to Flask for better performance and scalability while retaining all features and modernizing design.

## Goals
- **Primary**: Improve performance (5x lighter, faster page loads)
- **Secondary**: Modern, responsive design; easier deployment; better scalability
- **Maintain**: All current features, shared business logic, data storage (YAML)

## Non-Goals
- New features beyond current functionality
- Database migration (keep YAML files)
- REST API for external clients
- Authentication/login (not in current app)
- Mobile-specific native app

## Technical Stack Decision

### Backend: Flask
**Why Flask over alternatives:**
- **vs Django**: Too heavyweight for this use case; Flask is lightweight, minimal boilerplate
- **vs FastAPI**: Overkill for server-rendered HTML; FastAPI shines for APIs
- **vs Streamlit (keep it)**: Performance issues, limited customization, heavyweight connections

**Decision**: Flask 3.x with Blueprint-based architecture

### Frontend: HTMX + Tailwind CSS
**Why HTMX over JavaScript frameworks:**
- **vs React/Vue**: Requires complex build tools, state management, learning curve
- **vs jQuery**: Legacy approach, no modern patterns
- **vs Vanilla JS**: Would require writing lots of code for AJAX/updates
- **HTMX**: Declarative HTML attributes, no build step, server-driven, minimal JS

**Why Tailwind CSS:**
- **vs Bootstrap**: More customizable, smaller bundle, utility-first approach
- **vs Custom CSS**: Faster development, consistent design system, responsive utilities
- **Tailwind**: Modern, performant, no custom CSS needed

**Decision**: HTMX 1.9+ for interactivity, Tailwind CSS 3.x for styling

### Real-time Updates: Flask-SocketIO
**Why WebSockets over alternatives:**
- **vs Long polling**: Less efficient, higher latency
- **vs Server-Sent Events (SSE)**: One-way only, HTMX polling adequate for most updates
- **vs HTTP/2 Push**: Browser support issues, complexity

**Decision**: Flask-SocketIO for job progress (bidirectional), HTMX polling for dashboard refresh

## Architecture

### Directory Structure
```
backup-manager/
├── app.py                    # Existing Streamlit app (unchanged)
├── flask_app.py              # New Flask entry point
├── flask_app/
│   ├── __init__.py           # Flask app factory
│   ├── config.py             # Configuration
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── dashboard.py      # Dashboard blueprint
│   │   ├── jobs.py           # Jobs blueprint
│   │   ├── settings.py       # Settings blueprint
│   │   └── logs.py           # Logs blueprint
│   ├── socketio_handlers.py  # WebSocket event handlers
│   ├── templates/
│   │   ├── base.html         # Base layout with nav
│   │   ├── dashboard.html
│   │   ├── jobs.html
│   │   ├── settings.html
│   │   └── logs.html
│   ├── static/
│   │   ├── css/
│   │   │   └── output.css    # Generated Tailwind CSS
│   │   └── js/
│   │       └── main.js       # Minimal custom JS
│   └── utils/
│       ├── template_filters.py  # Jinja2 custom filters
│       └── htmx_helpers.py      # HTMX response utilities
├── core/                     # Shared business logic (unchanged)
├── engines/                  # Shared engines (unchanged)
├── storage/                  # Shared storage (unchanged)
├── models/                   # Shared models (unchanged)
└── utils/                    # Shared utilities (unchanged)
```

### Request Flow

**Standard Page Load:**
1. Browser → GET /dashboard
2. Flask route handler → Jinja2 template → HTML response
3. Browser receives HTML with HTMX attributes
4. Tailwind CSS classes provide styling

**HTMX Interaction (e.g., Start Job):**
1. User clicks "Start" button with `hx-post="/jobs/{id}/start"`
2. HTMX sends AJAX POST to Flask
3. Flask starts job, returns HTML fragment
4. HTMX swaps fragment into page (no full reload)

**Real-time Progress (WebSocket):**
1. Page loads, JavaScript connects to Socket.IO
2. Flask-SocketIO emits progress events
3. JS updates progress bars/status in real-time
4. Minimal custom JavaScript required

**Dashboard Auto-refresh (HTMX Polling):**
1. Dashboard includes `hx-get="/api/dashboard/stats" hx-trigger="every 2s"`
2. HTMX polls endpoint every 2 seconds
3. Flask returns updated HTML fragment
4. HTMX swaps new content (live updates without WebSocket)

### Session Management

**Flask Sessions:**
- Server-side sessions using Flask-Session (filesystem backend)
- Store: crash recovery prompt state, form data, user preferences
- Similar to Streamlit's st.session_state but more standard

### Error Handling

**Strategy:**
- Flash messages for user-facing errors
- HTMX error responses with `HX-Retarget` for inline errors
- Logging to file (same as current app)
- Error pages (404, 500) with consistent styling

### Performance Optimizations

**HTMX Optimizations:**
- `hx-boost` for navigation (faster page transitions)
- `hx-swap` with `outerHTML` for efficient updates
- Debounce search inputs (`hx-trigger="keyup changed delay:500ms"`)

**Caching:**
- Static assets cached with Cache-Control headers
- Job list caching (invalidate on changes)
- Tailwind CSS purged for production (remove unused classes)

**Connection Pooling:**
- WebSocket connection pooling for multiple tabs
- Graceful degradation if WebSocket fails (fall back to polling)

## Decisions

### Decision 1: Blueprint-based Architecture
**Options:**
- Single app.py with all routes
- Blueprint-based (separate modules per page)
- Flask-RESTful (API-first)

**Choice**: Blueprint-based
**Rationale**: Better organization, matches current 4-page structure, easier to maintain/test

### Decision 2: HTMX over Full SPA
**Options:**
- HTMX (server-rendered, minimal JS)
- React/Vue (client-side SPA)
- jQuery + Bootstrap (traditional approach)

**Choice**: HTMX
**Rationale**: Simplest possible (user requirement), no build tools, server-side logic, fast development

### Decision 3: Tailwind CSS over Bootstrap
**Options:**
- Tailwind CSS (utility-first)
- Bootstrap (component-based)
- Custom CSS

**Choice**: Tailwind CSS
**Rationale**: Modern design (user requirement), smaller bundle, faster iteration, no custom CSS

### Decision 4: Keep YAML Storage
**Options:**
- Migrate to SQLite/PostgreSQL
- Keep YAML files
- Use JSON instead

**Choice**: Keep YAML
**Rationale**: Already works, no migration pain, both apps can share storage, simple for small datasets

### Decision 5: Parallel Deployment
**Options:**
- Big bang replacement (remove Streamlit immediately)
- Parallel deployment (both run simultaneously)
- Feature flag toggle

**Choice**: Parallel deployment
**Rationale**: Lower risk, users can test, gradual migration, easy rollback

## Risks / Trade-offs

### Risk 1: HTMX Learning Curve
**Risk**: Team unfamiliar with HTMX, might be harder to maintain
**Mitigation**: HTMX is simpler than React/Vue; excellent docs; small API surface; fallback to vanilla JS possible

### Risk 2: WebSocket Stability
**Risk**: WebSocket connections can be unreliable (firewalls, proxies)
**Mitigation**: Graceful degradation to HTMX polling; reconnection logic; user sees stale data but app still works

### Risk 3: Tailwind CSS Bundle Size
**Risk**: Tailwind CSS can be large if not purged
**Mitigation**: Use Tailwind CLI with purge enabled; only ship used classes; ~10KB gzipped for this app

### Risk 4: Feature Parity
**Risk**: Missing features or bugs during migration
**Mitigation**: Comprehensive feature checklist; side-by-side testing; keep Streamlit until Flask is proven

### Risk 5: Performance Regression
**Risk**: Flask might not be faster in practice
**Mitigation**: Benchmarking before/after; profiling; caching strategies; can revert if needed

## Migration Plan

### Phase 1: Setup (Week 1)
- Scaffold Flask app structure
- Set up Tailwind CSS build
- Configure Flask-SocketIO
- Create base template with navigation

### Phase 2: Settings & Logs (Week 1-2)
- Migrate Settings page (mostly forms, simplest)
- Migrate Logs page (read-only, no real-time)
- Test form handling, file operations

### Phase 3: Dashboard (Week 2-3)
- Migrate Dashboard page
- Implement HTMX polling for auto-refresh
- Add stats display
- Test real-time updates

### Phase 4: Jobs Page (Week 3-4)
- Migrate Jobs page (most complex)
- Implement WebSocket progress updates
- Add CRUD operations (create, start, pause, delete)
- Test crash recovery

### Phase 5: Testing & Polish (Week 4-5)
- Comprehensive feature testing
- Performance benchmarking
- Responsive design testing
- Error handling edge cases
- User acceptance testing

### Phase 6: Deployment (Week 5)
- Production deployment guide
- Nginx configuration
- Supervisor/systemd service
- Graceful cutover from Streamlit

## Open Questions

1. **Port allocation**: Flask on 5000, Streamlit on 8501? (Assumed yes)
2. **Authentication**: Add login/auth? (Assumed no - out of scope)
3. **Color scheme**: Specific branding? (Assumed generic blue/gray palette)
4. **Analytics**: Track usage metrics? (Assumed no - out of scope)
5. **Docker**: Containerize Flask app? (Assumed optional, can add later)

## Success Criteria

**Performance:**
- Page load < 500ms (vs 1-2s with Streamlit)
- Job start response < 200ms
- Real-time updates < 100ms latency

**Functionality:**
- 100% feature parity with Streamlit
- All existing tests pass
- No regressions in job execution

**Usability:**
- Modern, responsive design
- Works on mobile devices
- Accessible (WCAG 2.1 AA)

**Deployment:**
- Simple production deployment
- Works with Gunicorn + Nginx
- Graceful shutdown/restart
