# Implementation Tasks

## Phase 1: Archive Streamlit Files

### Task 1.1: Create archive directory
**Location**: Root directory
**Action**: Create `archive/streamlit/` directory structure

**Steps**:
```bash
mkdir -p archive/streamlit
```

**Validation**: Directory exists and is empty

---

### Task 1.2: Move Streamlit files to archive
**Location**: Root → `archive/streamlit/`
**Action**: Move original Streamlit application files

**Steps**:
```bash
mv app.py archive/streamlit/
mv app.py.bak archive/streamlit/
```

**Validation**:
- `archive/streamlit/app.py` exists (59KB)
- `archive/streamlit/app.py.bak` exists (57KB)
- Root `app.py` no longer exists

---

### Task 1.3: Create archive README
**Location**: `archive/streamlit/README.md`
**Action**: Document archived Streamlit application

**Content**:
```markdown
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
```

**Validation**: README exists and is readable

---

## Phase 2: Create Flask Redirect Stub

### Task 2.1: Create redirect stub
**Location**: `app.py` (root)
**Action**: Create Python script that prints migration message

**Content**:
```python
#!/usr/bin/env python3
"""
Streamlit UI has been retired.

The backup-manager application now uses Flask for better performance
and scalability. Please use the Flask application instead.

Quick Start:
  uv run python flask_app.py

The Flask app will be available at:
  http://localhost:5001

For more information, see:
  - FLASK_MIGRATION_COMPLETE.md
  - README.md

The original Streamlit app is archived in:
  archive/streamlit/app.py
"""
import sys

def main():
    print(__doc__)
    print("\n" + "="*70)
    print("ERROR: Streamlit UI retired - Use Flask instead")
    print("="*70)
    print("\nRun this command to start the Flask app:")
    print("  uv run python flask_app.py")
    print()
    sys.exit(1)

if __name__ == "__main__":
    main()
```

**Validation**:
- Running `python app.py` prints helpful message
- Script exits with code 1

---

## Phase 3: Update Documentation

### Task 3.1: Update install.sh
**Location**: `install.sh:77`
**Action**: Replace Streamlit start command with Flask

**Before**:
```bash
echo "  uv run streamlit run app.py"
```

**After**:
```bash
echo "  uv run python flask_app.py"
```

**Validation**: Script prints Flask command

---

### Task 3.2: Update TESTING.md
**Location**: `TESTING.md:26` and `TESTING.md:133`
**Action**: Replace Streamlit commands with Flask

**Changes**:
- Line 26: Replace `uv run streamlit run app.py` → `uv run python flask_app.py`
- Line 133: Replace `uv run streamlit run app.py` → `uv run python flask_app.py`

**Validation**: `rg "streamlit run" TESTING.md` returns no matches

---

### Task 3.3: Update setup_jobs.py
**Location**: `setup_jobs.py:169`
**Action**: Update printed start command

**Before**:
```python
print("  uv run streamlit run app.py")
```

**After**:
```python
print("  uv run python flask_app.py")
```

**Validation**: Running script prints Flask command

---

### Task 3.4: Clean up requirements.txt
**Location**: `requirements.txt:18-20`
**Action**: Remove commented Streamlit dependency lines

**Before**:
```
# Legacy (Streamlit - can be removed once migration is complete)
# streamlit>=1.28.0
# streamlit-autorefresh>=1.0.1
```

**After**: (lines removed entirely)

**Validation**:
- `rg "streamlit" requirements.txt` returns no matches
- File still has all Flask dependencies intact

---

### Task 3.5: Update FLASK_MIGRATION_COMPLETE.md (optional)
**Location**: `FLASK_MIGRATION_COMPLETE.md:137-144`
**Action**: Add note that Streamlit is now archived

**Add after line 144**:
```markdown

**Note:** As of 2025-10-26, the Streamlit app has been archived to `archive/streamlit/`.
Flask is now the sole supported UI. See the archive README for restoration instructions.
```

**Validation**: Document mentions archive location

---

## Phase 4: Validation & Testing

### Task 4.1: Search for remaining references
**Action**: Verify no active Streamlit references remain

**Commands**:
```bash
# Should only show archived files and historical docs
rg -n "streamlit run" .

# Should not show any active references
rg -n "streamlit run" --glob '!archive/**' --glob '!openspec/changes/archive/**'
```

**Expected**: No active references outside archives

---

### Task 4.2: Verify Flask still works
**Action**: Test Flask application launches successfully

**Steps**:
```bash
uv run python flask_app.py
```

**Expected**:
- Flask starts on port 5001
- Dashboard loads at http://localhost:5001
- All pages accessible
- Jobs/Settings/Logs functional

---

### Task 4.3: Test stub behavior
**Action**: Verify stub provides helpful message

**Steps**:
```bash
python app.py
```

**Expected**:
- Clear error message printed
- Instructions to use Flask
- Exit code 1

---

## Summary

**Files Created:**
- `archive/streamlit/` directory (3 files)
- `archive/streamlit/README.md` (new)
- `app.py` (stub, replaces original)

**Files Modified:**
- `install.sh` (1 line)
- `TESTING.md` (2 lines)
- `setup_jobs.py` (1 line)
- `requirements.txt` (3 lines removed)
- `FLASK_MIGRATION_COMPLETE.md` (1 note added, optional)

**Files Deleted:**
- None (all preserved in archive)

**Total Changes:** 5 files modified, 3 files moved, 2 files created
