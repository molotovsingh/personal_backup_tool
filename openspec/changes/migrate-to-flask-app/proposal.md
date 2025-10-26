# Proposal: Migrate from Streamlit to Flask

## Why
The current Streamlit implementation has performance and scalability limitations that impact user experience. Streamlit's architecture requires full page reloads and maintains heavyweight server connections, leading to slower response times and higher resource usage. Migrating to Flask provides better performance (~5x lighter), full control over UI/UX, easier deployment (standard WSGI), and better scalability for concurrent users.

## What Changes
- **New Flask application**: Build Flask + HTMX + Tailwind CSS app alongside existing Streamlit app
- **Retain all features**: Dashboard, Jobs, Settings, Logs pages with identical functionality
- **Modernize design**: Clean, responsive UI using Tailwind CSS utility classes
- **Real-time updates**: WebSocket (Flask-SocketIO) for live progress, HTMX polling for dashboard
- **Shared business logic**: Both apps use same core/ engines/ storage/ models/ utils/ modules
- **Parallel deployment**: Flask on port 5000, Streamlit remains on 8501 until migration complete

## Impact
- **Affected specs**: 6 new capabilities (flask-application-structure, dashboard-page, jobs-page, settings-page, logs-page, real-time-updates)
- **Affected code**: New `flask_app/` directory with all Flask code; no changes to core business logic
- **No breaking changes**: Existing Streamlit app continues to work; shared modules remain compatible
- **Migration path**: Users can test Flask version before switching; gradual cutover
- **Dependencies**: Add Flask, Flask-SocketIO, python-socketio, tailwindcss-cli to requirements
- **Deployment**: Standard WSGI app, works with Gunicorn/Nginx (easier than Streamlit)
- **Testing**: All existing features must work identically; performance benchmarks required
