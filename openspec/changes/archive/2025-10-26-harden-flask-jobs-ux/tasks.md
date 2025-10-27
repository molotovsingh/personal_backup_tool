# Implementation Tasks

## Phase 1: Deletion Checkbox Robustness

### Task 1.1: Add HTMX Synchronization

**Location**: `flask_app/templates/jobs.html:106-115`

**Action**: Add `hx-sync` attribute to prevent race conditions during rapid toggling

**Changes**:
```html
<input type="checkbox"
       id="delete_source_after"
       name="delete_source_after"
       value="true"
       class="mr-3 w-4 h-4 text-red-600 focus:ring-red-500"
       hx-get="/jobs/deletion-ui"
       hx-trigger="change"
       hx-target="#deletion-options"
       hx-swap="innerHTML"
       hx-sync="closest form:drop"
       hx-vals='js:{"delete_source_after": this.checked}'>
```

**Validation**: Rapid toggling drops in-flight requests

---

### Task 1.2: Add Loading Indicator

**Location**: `flask_app/templates/jobs.html` (after checkbox input)

**Action**: Add loading indicator and hx-indicator attribute

**Changes**:
```html
<input type="checkbox"
       ...
       hx-indicator=".deletion-options-indicator"
       ...>
<span class="deletion-options-indicator htmx-indicator ml-2 text-xs text-gray-400">Loading…</span>
```

**CSS Note**: HTMX automatically shows/hides elements with class `htmx-indicator`

**Validation**: "Loading…" appears briefly when toggling

---

### Task 1.3: Add Error Handling

**Location**: `flask_app/templates/jobs.html:106`

**Action**: Add network error handler

**Changes**:
```html
<input type="checkbox"
       ...
       hx-on::request-error="document.getElementById('deletion-options').innerHTML = '<div class=\"text-red-700 text-sm\">Failed to load options. Try again.</div>'"
       ...>
```

**Validation**: Simulate network error (kill server mid-request), verify error message appears

---

### Task 1.4: Add ARIA Attributes

**Location**: `flask_app/templates/jobs.html:106`

**Action**: Add accessibility attributes

**Changes**:
```html
<input type="checkbox"
       ...
       aria-controls="deletion-options"
       aria-expanded="false"
       hx-on:change="this.setAttribute('aria-expanded', this.checked)"
       ...>
```

**Validation**: Screen reader announces checkbox controls deletion options

---

### Task 1.5: Make Deletion Options Live Region

**Location**: `flask_app/templates/jobs.html:125`

**Action**: Add ARIA live region attributes

**Changes**:
```html
<div id="deletion-options"
     class="mt-3"
     role="region"
     aria-live="polite"
     aria-label="Deletion options"></div>
```

**Validation**: Screen reader announces when deletion options appear

---

## Phase 2: Deletion Options Accessibility

### Task 2.1: Add Fieldset Wrapper

**Location**: `flask_app/templates/partials/deletion_options.html`

**Action**: Wrap radio group in semantic fieldset

**Before**:
```html
{% if show_options %}
<div class="space-y-3 mt-3">
    <label class="block text-sm font-medium text-gray-700 mb-2">
        Deletion Mode *
    </label>
    <!-- radio inputs -->
</div>
{% endif %}
```

**After**:
```html
{% if show_options %}
<fieldset class="space-y-3 mt-3">
    <legend class="block text-sm font-medium text-gray-700 mb-2">
        Deletion Mode *
    </legend>
    <!-- radio inputs -->
</fieldset>
{% endif %}
```

**Validation**: Screen reader announces "Deletion Mode" as group label

---

## Phase 3: Crash Recovery Polish

### Task 3.1: Add Recover Button Helper Text

**Location**: `flask_app/templates/base.html:56-61`

**Action**: Add explanatory text and disable-on-click

**Changes**:
```html
<form action="/recover-jobs" method="POST">
    <button type="submit"
            class="w-full bg-green-600 text-white px-3 py-2 rounded text-sm hover:bg-green-700 transition"
            onclick="this.disabled=true; this.form.submit();">
        ✅ Recover (mark as paused)
    </button>
    <p class="mt-1 text-xs text-green-200">Ensures safe state; resume later from Jobs.</p>
</form>
```

**Validation**: Button disables immediately on click, helper text visible

---

### Task 3.2: Add Dismiss Button Disable-on-Click

**Location**: `flask_app/templates/base.html:62-67`

**Action**: Prevent double-submit on dismiss button

**Changes**:
```html
<form action="/dismiss-recovery" method="POST">
    <button type="submit"
            class="w-full bg-gray-700 text-gray-200 px-3 py-2 rounded text-sm hover:bg-gray-600 transition"
            onclick="this.disabled=true; this.form.submit();">
        Dismiss
    </button>
</form>
```

**Validation**: Button disables immediately on click

---

## Phase 4: Test Coverage

### Task 4.1: Create Deletion UI Partial Tests

**Location**: `tests/test_deletion_ui_partial.py` (new file)

**Action**: Create test file

**Content**:
```python
"""Test deletion UI partial endpoint."""
import pytest

def test_deletion_ui_true(client):
    """Test deletion UI returns content when delete_source_after=true."""
    resp = client.get('/jobs/deletion-ui?delete_source_after=true')
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert 'id="deletion_confirmed"' in html
    assert 'value="verify_then_delete"' in html
    assert 'Deletion Mode' in html

def test_deletion_ui_false(client):
    """Test deletion UI returns empty when delete_source_after=false."""
    resp = client.get('/jobs/deletion-ui?delete_source_after=false')
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert 'id="deletion_confirmed"' not in html
    assert 'Deletion Mode' not in html

def test_deletion_ui_missing_param(client):
    """Test deletion UI handles missing parameter gracefully."""
    resp = client.get('/jobs/deletion-ui')
    assert resp.status_code == 200
```

**Validation**: Run `pytest tests/test_deletion_ui_partial.py -v`

---

### Task 4.2: Create Crash Recovery Prompt Test

**Location**: `tests/test_crash_recovery_prompt.py` (new file)

**Action**: Create test file

**Content**:
```python
"""Test crash recovery prompt rendering."""
import pytest

def test_crash_recovery_prompt_rendered(client):
    """Test crash recovery prompt appears when interrupted jobs exist."""
    with client.session_transaction() as sess:
        sess['interrupted_jobs'] = ['job1', 'job2']
        sess['show_recovery_prompt'] = True
        sess['interrupted_job_count'] = 2

    resp = client.get('/')
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert 'Crash Detected' in html
    assert 'Recover (mark as paused)' in html
    assert 'Dismiss' in html
    assert '2 interrupted job(s)' in html

def test_no_crash_recovery_when_no_interrupted_jobs(client):
    """Test crash recovery prompt does not appear when no interrupted jobs."""
    resp = client.get('/')
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert 'Crash Detected' not in html
    assert 'Recover (mark as paused)' not in html
```

**Validation**: Run `pytest tests/test_crash_recovery_prompt.py -v`

---

### Task 4.3: Create Test Fixtures

**Location**: `tests/conftest.py` (may need updates)

**Action**: Ensure Flask test client fixture exists

**Content** (if needed):
```python
"""Pytest configuration and fixtures."""
import pytest
from flask_app import create_app

@pytest.fixture
def app():
    """Create Flask app for testing."""
    app = create_app()
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret-key'
    yield app

@pytest.fixture
def client(app):
    """Create Flask test client."""
    return app.test_client()
```

**Validation**: Run `pytest --collect-only` to verify fixtures available

---

## Phase 5: Validation & Testing

### Task 5.1: Manual Testing - Rapid Toggle

**Steps**:
1. Open http://localhost:5001/jobs/
2. Click "+ Create New Job"
3. Rapidly toggle deletion checkbox 5-10 times
4. Observe loading indicator appears
5. Verify deletion options appear/disappear smoothly

**Expected**:
- Loading indicator shows briefly
- No stale UI states
- Final state matches checkbox state

---

### Task 5.2: Manual Testing - Network Error

**Steps**:
1. Open jobs page with deletion checkbox
2. Open browser DevTools Network tab
3. Enable "Offline" mode
4. Toggle deletion checkbox

**Expected**:
- Error message appears in deletion-options area
- Message: "Failed to load options. Try again."

---

### Task 5.3: Manual Testing - Crash Recovery

**Steps**:
1. Manually set a job status to 'running' in storage
2. Restart Flask app
3. Open http://localhost:5001/
4. Verify crash recovery prompt appears
5. Click "Recover (mark as paused)"

**Expected**:
- Helper text visible
- Button disables immediately
- Jobs marked as paused

---

### Task 5.4: Accessibility Testing

**Steps**:
1. Use screen reader (NVDA/JAWS/VoiceOver)
2. Navigate to deletion checkbox
3. Toggle checkbox

**Expected**:
- Announces "Delete source files after successful backup, checkbox"
- Announces "controls deletion options"
- Announces when expanded/collapsed
- Announces "Deletion Mode" fieldset when options appear

---

### Task 5.5: Run All Tests

**Command**:
```bash
pytest tests/test_deletion_ui_partial.py tests/test_crash_recovery_prompt.py -v
```

**Expected**: All tests pass

---

## Summary

**Total Tasks**: 14 tasks across 5 phases

**Files Modified**:
- `flask_app/templates/jobs.html` (deletion checkbox enhancements)
- `flask_app/templates/partials/deletion_options.html` (fieldset wrapper)
- `flask_app/templates/base.html` (crash recovery polish)

**Files Created**:
- `tests/test_deletion_ui_partial.py` (3 test cases)
- `tests/test_crash_recovery_prompt.py` (2 test cases)
- `tests/conftest.py` (fixtures, if needed)

**Estimated Time**: 2-3 hours
- Code changes: 30-45 minutes
- Test creation: 45-60 minutes
- Manual testing: 30-45 minutes
- Accessibility testing: 15-30 minutes

**Success Criteria**:
- ✅ Rapid toggling shows loading indicator
- ✅ Network errors display error message
- ✅ Screen readers announce properly
- ✅ Crash recovery buttons disable on click
- ✅ All automated tests pass
