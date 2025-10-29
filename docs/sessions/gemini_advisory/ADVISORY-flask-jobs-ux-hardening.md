# UX Advisory — Flask Jobs: Deletion Controls and Crash Recovery Hardening

Summary

- Verified the deletion checkbox flicker fix is correct and robust via server‑driven HTMX.
- Recommend small, low‑risk enhancements for resilience, accessibility, and clarity.
- Scope is limited to templates and minor client UX behaviors; no backend logic changes required.

Verification

- Deletion control
  - `flask_app/templates/jobs.html:107` — Checkbox uses `hx-get="/jobs/deletion-ui"` with `hx-vals` reflecting `this.checked`.
  - `flask_app/routes/jobs.py:30` — `deletion_ui()` reads `delete_source_after` and returns the correct partial.
  - `flask_app/templates/partials/deletion_options.html:1` — Renders radio options and a required confirmation checkbox.
- Crash recovery
  - `flask_app/templates/base.html:43` — Prompt with “Recover (mark as paused)” and “Dismiss”.
  - `flask_app/routes/dashboard.py:72` — Recover marks interrupted jobs paused; Dismiss only hides prompt.
  - `flask_app/__init__.py:85` — Detects interrupted jobs and injects `show_recovery_prompt` + count.

Recommendations

1) Robustness for rapid toggles (low risk)
- Problem: Quick toggling can send multiple HTMX requests; last response may not win deterministically.
- Changes:
  - Add `hx-sync="closest form:drop"` to drop in‑flight requests when a new one is issued.
  - Add a tiny inline indicator for visual feedback while fetching.
  - Add inline error handling for network failures.

Patch (conceptual)

```html
<!-- flask_app/templates/jobs.html: around the deletion checkbox -->
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
       hx-indicator=".deletion-options-indicator"
       hx-on::request-error="document.getElementById('deletion-options').innerHTML = '<div class=&quot;text-red-700 text-sm&quot;>Failed to load options. Try again.</div>'"
       hx-vals='js:{"delete_source_after": this.checked}'
       aria-controls="deletion-options"
       aria-expanded="false"
       hx-on:change="this.setAttribute('aria-expanded', this.checked)">
<span class="deletion-options-indicator htmx-indicator ml-2 text-xs text-gray-400">Loading…</span>

<!-- Make target an ARIA live region -->
<div id="deletion-options" class="mt-3" role="region" aria-live="polite" aria-label="Deletion options"></div>
```

2) Accessibility/semantics for deletion options (very low risk)
- Problem: Radio group lacks form semantics beyond labels; screen reader flow can be clearer.
- Change: Wrap radio options in a fieldset + legend.

Patch (conceptual)

```html
<!-- flask_app/templates/partials/deletion_options.html -->
{% if show_options %}
<fieldset>
  <legend class="block text-sm font-medium text-gray-700 mb-2">Deletion Mode *</nlegend>
  <!-- existing radio labels... -->
</fieldset>
{% endif %}
```

3) Crash recovery prompt UX polish (very low risk)
- Problem: Actions are correct, but minor clarity and robustness improvements help.
- Changes:
  - Add one‑line helper text under “Recover (mark as paused)”.
  - Disable buttons after click to prevent double submit.

Patch (conceptual)

```html
<!-- flask_app/templates/base.html: crash recovery prompt -->
<form action="/recover-jobs" method="POST">
  <button type="submit"
          class="w-full bg-green-600 text-white px-3 py-2 rounded text-sm hover:bg-green-700 transition"
          onclick="this.disabled=true; this.form.submit();">
    ✅ Recover (mark as paused)
  </button>
  <p class="mt-1 text-xs text-green-200">Ensures safe state; resume later from Jobs.</p>
  </form>
<form action="/dismiss-recovery" method="POST">
  <button type="submit"
          class="w-full bg-gray-700 text-gray-200 px-3 py-2 rounded text-sm hover:bg-gray-600 transition"
          onclick="this.disabled=true; this.form.submit();">
    Dismiss
  </button>
</form>
```

4) Tests (small additions)
- File: `tests/test_deletion_ui_partial.py`
  - Case 1: GET `/jobs/deletion-ui?delete_source_after=true` returns content containing `id="deletion_confirmed"` and radio value `verify_then_delete`.
  - Case 2: GET `/jobs/deletion-ui?delete_source_after=false` returns empty body (or no radio markup).
- File: `tests/test_crash_recovery_prompt.py`
  - Case: Simulate session with interrupted jobs and GET `/`; assert the prompt is rendered with “Recover (mark as paused)”.

Example test snippets

```python
# tests/test_deletion_ui_partial.py
def test_deletion_ui_true(client):
    resp = client.get('/jobs/deletion-ui?delete_source_after=true')
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert 'id="deletion_confirmed"' in html
    assert 'value="verify_then_delete"' in html

def test_deletion_ui_false(client):
    resp = client.get('/jobs/deletion-ui?delete_source_after=false')
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert 'id="deletion_confirmed"' not in html
```

```python
# tests/test_crash_recovery_prompt.py
def test_crash_recovery_prompt_rendered(client, monkeypatch):
    with client.session_transaction() as sess:
        sess['interrupted_jobs'] = ['job1']
        sess['show_recovery_prompt'] = True
    resp = client.get('/')
    assert resp.status_code == 200
    html = resp.get_data(as_text=True)
    assert 'Recover (mark as paused)' in html
```

Impact

- No backend logic changes.
- Minimal template updates and a couple of small tests.
- Improved resilience (no stale HTMX updates), accessibility (ARIA), and UX clarity.

Status

- Advice only. Safe to implement in a single, small PR.

