# Fix Deletion Checkbox Flicker

## Why

The deletion checkbox in the job creation form uses conflicting client-side and server-side logic, causing UI flicker and preventing users from reliably configuring deletion options. This creates a poor user experience and blocks a critical workflow.

## Problem

When creating a new job, clicking the "Delete source files after successful backup" checkbox causes:

1. **UI Flicker** - Deletion options appear briefly then disappear
2. **Race Condition** - Client-side `onclick` handler conflicts with HTMX `hx-get` request
3. **Broken UX** - Users cannot configure deletion mode (verify_then_delete vs per_file)
4. **Maintenance Burden** - Two competing mechanisms (JavaScript + HTMX) for same functionality

**Evidence:**
- Current code: `flask_app/templates/jobs.html:106-115`
- Uses both `hx-get="/jobs/deletion-ui?delete_source_after=true"` (hardcoded)
- AND `onclick="if(!this.checked) document.getElementById('deletion-options').innerHTML = ''"`
- Server-side code already handles dynamic `delete_source_after` parameter correctly: `flask_app/routes/jobs.py:30-34`

**Root Cause:**
The checkbox always sends `delete_source_after=true` to the server regardless of checked state, while the `onclick` handler manually clears the UI when unchecked. This creates a race condition where both mechanisms fight for control.

## Solution

Refactor to use a **single, server-driven approach** by:

1. **Remove `onclick` handler** - Eliminate client-side logic conflict
2. **Use `hx-vals` with JavaScript** - Dynamically send checkbox state to server
3. **Let server decide** - Backend returns UI for checked, empty for unchecked
4. **Keep server-side code unchanged** - Already handles boolean parameter correctly

**Approach:** Replace hardcoded `?delete_source_after=true` with `hx-vals='js:{"delete_source_after": this.checked}'`. This is idiomatic HTMX and aligns with the server's existing implementation.

## Scope

**In Scope:**
- Update deletion checkbox HTMX attributes in `jobs.html`
- Remove conflicting `onclick` JavaScript handler
- Verify server-side handler works with dynamic parameter (already does)

**Out of Scope:**
- Changes to server-side logic (already correct)
- Changes to deletion_options.html partial template
- New deletion features or modes
- Other HTMX interactions in the form

## Impact

**Benefits:**
- **Fixed UX** - Deletion options appear/disappear reliably
- **No Flicker** - Single server-driven mechanism eliminates race condition
- **Maintainability** - One mechanism instead of two
- **HTMX Best Practice** - Server as single source of truth

**Risks:**
- Very low - Small, well-understood change
- Server-side code already supports this pattern
- No changes to business logic

**User Impact:**
- Users can now configure deletion options without flicker
- More responsive UI (no JavaScript manipulation delay)
- Clearer interaction model

## Files to Modify

**Single File Change:**

`flask_app/templates/jobs.html` (lines 106-115)

**Before:**
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

**After:**
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

**Changes:**
1. Remove `?delete_source_after=true` from `hx-get` URL
2. Add `hx-vals='js:{"delete_source_after": this.checked}'`
3. Remove `onclick` handler entirely

## Validation

- [ ] Checkbox checked → deletion options appear
- [ ] Checkbox unchecked → deletion options disappear
- [ ] No UI flicker during state changes
- [ ] Can create job with deletion enabled and mode selected
- [ ] Can create job with deletion disabled
