# Retire Streamlit App

## Why

The Flask UI is now the production-ready interface with full feature parity, better performance, and modern architecture. Keeping Streamlit creates maintenance burden and user confusion with two entry points for the same application.

## Problem

The Flask migration is complete with full feature parity and better performance (5-10x faster page loads, real-time WebSocket updates, production-ready architecture). The legacy Streamlit UI (`app.py`, 59KB) remains in the codebase and is still referenced in developer documentation and scripts, creating:

1. **User confusion** - Two UIs serving the same purpose
2. **Maintenance burden** - Keeping docs/scripts in sync with two entry points
3. **Risk of divergence** - Potential for bugs/features to diverge between UIs
4. **Cluttered codebase** - `app.py` and `app.py.bak` no longer actively used

**Evidence:**
- Flask migration complete: `FLASK_MIGRATION_COMPLETE.md:1-817` (100% feature parity)
- Streamlit still referenced: `install.sh:77`, `TESTING.md:26,133`, `setup_jobs.py:169`
- Commented Streamlit deps: `requirements.txt:18-20`

## Solution

Archive the Streamlit application in a clean, reversible manner:

1. **Archive Streamlit files** - Move `app.py` and `app.py.bak` to `archive/streamlit/` directory
2. **Add migration stub** - Create informative `app.py` stub that redirects users to Flask
3. **Update documentation** - Replace all Streamlit references with Flask commands
4. **Clean up dependencies** - Remove commented Streamlit lines from requirements
5. **Validate transition** - Ensure all workflows now point to Flask

**Approach:** Immediate cutover (no deprecation window) since this is a solo/local development tool. The archive directory preserves the ability to restore Streamlit if needed.

## Scope

**In Scope:**
- Move Streamlit files to archive
- Update all documentation references
- Remove commented dependencies
- Create helpful redirect stub

**Out of Scope:**
- Removing business logic (already shared between UIs)
- Changes to Flask application
- New features or enhancements

## Impact

**Benefits:**
- Single UI to maintain (Flask)
- Clear user path (no confusion)
- Cleaner codebase
- Reduced documentation maintenance

**Risks:**
- Low - Streamlit files preserved in archive for quick restoration if needed
- Flask already proven to work with all features

**User Impact:**
- Users running `streamlit run app.py` will see helpful message to use Flask
- All existing jobs/settings/data unaffected (shared YAML storage)

## Files to Modify

1. **Archive creation** (new):
   - `archive/streamlit/app.py` (moved)
   - `archive/streamlit/app.py.bak` (moved)
   - `archive/streamlit/README.md` (new)

2. **Stub creation**:
   - `app.py` (replaced with redirect message)

3. **Documentation updates**:
   - `install.sh:77` - Update start command
   - `TESTING.md:26,133` - Replace Streamlit commands
   - `setup_jobs.py:169` - Update printed guidance
   - `requirements.txt:18-20` - Remove commented lines
   - `FLASK_MIGRATION_COMPLETE.md` - Note Streamlit archived (optional)

## Validation

- [ ] Archive directory exists with Streamlit files
- [ ] Stub `app.py` prints helpful message when invoked
- [ ] All docs reference Flask, not Streamlit
- [ ] `rg -n "streamlit run" .` shows no active references (outside archive)
- [ ] Flask app still works: `uv run python flask_app.py`
