# Deletion Options Not Loading - Diagnosis

## Problem
From screenshot: User checks deletion checkbox but deletion options (radio buttons, confirmation checkbox) do NOT appear.

## What We See
✅ Deletion checkbox is checked
✅ Warning message appears below checkbox
❌ **Deletion Mode radio buttons - MISSING**
❌ **Confirmation checkbox - MISSING**
❌ Error message at bottom: "You must confirm the deletion risks to enable source deletion"

## Root Cause Candidates

### 1. HTMX Not Loaded
Check if HTMX library is loaded in base.html

### 2. HTMX Request Not Firing
Checkbox might not be triggering the GET request to `/jobs/deletion-ui`

### 3. JavaScript Error
The `hx-on::request-error` attribute has escaped HTML entities that might cause parsing error

### 4. Target Div Issue
The `#deletion-options` div might not exist or be outside the form

### 5. hx-sync Blocking
The `hx-sync="closest form:drop"` might be preventing first request

## Diagnostic Steps

**Step 1: Open Browser DevTools (F12)**

**Step 2: Check Console tab**
- Look for any red JavaScript errors
- Look for HTMX initialization message

**Step 3: Check Network tab**
- Filter by "deletion-ui"
- Check the box
- See if request to `/jobs/deletion-ui?delete_source_after=true` appears
- If YES: Check response (should be HTML)
- If NO: HTMX not triggering

**Step 4: Check Elements tab**
- Find the `<input id="delete_source_after">` checkbox
- Look at its attributes
- Verify `hx-get`, `hx-trigger`, `hx-target` are present
- Find `<div id="deletion-options">` - verify it exists and is inside `<form>`

## Quick Test
In browser console, run:
```javascript
// Check if HTMX is loaded
typeof htmx

// Should return "object" if loaded
// Should return "undefined" if NOT loaded
```

## Expected Behavior
When checkbox is checked:
1. HTMX detects `change` event
2. HTMX sends GET `/jobs/deletion-ui?delete_source_after=true`
3. Server returns HTML with deletion options
4. HTMX swaps HTML into `#deletion-options` div
5. User sees deletion mode radio buttons and confirmation checkbox

## Most Likely Issue
Based on the screenshot showing NO content at all, I suspect either:
- HTMX request is silently failing
- JavaScript error preventing HTMX from running
- The `hx-vals` JavaScript is malformed

Let me check the hx-vals attribute...
