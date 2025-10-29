# Advisory: Job Deletion UI Flickering and Race Condition

## 1. Problem Summary

When creating a new job, clicking the "Delete source files after successful backup" checkbox causes a UI "flicker", but the deletion options do not appear as expected. This prevents users from configuring the deletion mode for jobs.

## 2. Root Cause Analysis

The issue stems from a conflicting and inefficient implementation in `flask_app/templates/jobs.html`. The checkbox element uses two competing mechanisms to control the UI:

1.  **Static `hx-get`:** The `hx-get` attribute is hardcoded to always request `/jobs/deletion-ui?delete_source_after=true`. This fetches the deletion options UI regardless of whether the box is being checked or unchecked.
2.  **`onclick` JavaScript:** A separate `onclick` handler (`if(!this.checked) ...`) is used to manually clear the UI only when the box is unchecked.

This creates a race condition, particularly when unchecking the box. More importantly, it leads to the reported "flicker" behavior and an unreliable user experience. The core problem is that the client-side `onclick` logic conflicts with the server-request logic from HTMX.

## 3. Proposed Solution

The recommended solution is to refactor the checkbox to use a single, server-driven approach, which is more robust and idiomatic for HTMX. This involves removing the client-side `onclick` handler and dynamically sending the checkbox's state to the server.

The server-side code in `flask_app/routes/jobs.py` is already correctly written to handle this approach; only the front-end template needs to be changed.

**File:** `/Users/aks/backup-manager/flask_app/templates/jobs.html`

**Current Implementation:**
```html
<input type="checkbox"
       id="delete_source_after"
       name="delete_source_after"
       value="true"
       class="mr-3 w-4 h-4 text-red-600 focus:ring-red-500"
       hx-get="/jobs/deletion-ui?delete_source_after=true"
       hx-trigger="change"
       hx-target="#deletion-options"
       hx-swap="innerHTML"
       onclick="if(!this.checked) document.getElementById('deletion-options').innerHTML = '';">
```

**Proposed Refactor:**
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
       hx-vals='js:{"delete_source_after": this.checked}'>
```

This change ensures that the server is the single source of truth, cleanly providing the UI when the box is checked and an empty response when it's unchecked, resolving the flicker and the bug.
