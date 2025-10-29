# Archived Streamlit Application

**Archived Date:** 2025-10-26
**Reason:** Replaced by Flask application (see FLASK_MIGRATION_COMPLETE.md)

## Files

- `app.py` - Original Streamlit UI (1320 lines)
- `app.py.bak` - Backup of Streamlit UI

## Restoration

To restore Streamlit (if needed):

1. Copy files back to root: `cp archive/streamlit/app.py .`
2. Install dependencies: `uv pip install streamlit streamlit-autorefresh`
3. Run: `uv run streamlit run app.py`

## Migration Notes

- Flask migration completed 2025-10-25
- 100% feature parity achieved
- 5-10x performance improvement
- All business logic shared (no duplication)
- See FLASK_MIGRATION_COMPLETE.md for details
