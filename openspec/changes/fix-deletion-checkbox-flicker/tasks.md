# Implementation Tasks

## Task 1: Update Deletion Checkbox HTMX Attributes

**Location**: `flask_app/templates/jobs.html:106-115`

**Action**: Replace checkbox element with server-driven HTMX approach

**Current Code**:
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

**New Code**:
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

**Changes**:
1. Line 111: Remove `?delete_source_after=true` query parameter
   - Before: `hx-get="/jobs/deletion-ui?delete_source_after=true"`
   - After: `hx-get="/jobs/deletion-ui"`

2. Line 115: Remove entire `onclick` attribute
   - Before: `onclick="if(!this.checked) document.getElementById('deletion-options').innerHTML = '';"`
   - After: (removed)

3. Add new attribute after `hx-swap` (line 114):
   - New: `hx-vals='js:{"delete_source_after": this.checked}'`

**Validation**:
- File syntax is valid HTML
- HTMX attributes properly formatted
- No JavaScript inline handlers remain
- Server endpoint `/jobs/deletion-ui` accepts `delete_source_after` parameter

---

## Task 2: Manual Testing

**Action**: Verify checkbox behavior in browser

### Test 2.1: Check Deletion Options
**Steps**:
1. Open Flask app: http://localhost:5001/jobs/
2. Click "+ Create New Job" button
3. Check "Delete source files after successful backup" checkbox

**Expected**:
- Deletion options UI appears smoothly (no flicker)
- Shows deletion mode dropdown
- Shows verification options

**Actual**: ____________________

---

### Test 2.2: Uncheck Deletion Options
**Steps**:
1. With deletion options visible
2. Uncheck "Delete source files after successful backup" checkbox

**Expected**:
- Deletion options UI disappears smoothly (no flicker)
- `#deletion-options` div becomes empty
- No JavaScript errors in browser console

**Actual**: ____________________

---

### Test 2.3: Toggle Multiple Times
**Steps**:
1. Check and uncheck the deletion checkbox 5 times rapidly

**Expected**:
- UI responds consistently each time
- No flicker or race conditions
- Options appear/disappear cleanly

**Actual**: ____________________

---

### Test 2.4: Create Job With Deletion Enabled
**Steps**:
1. Check deletion checkbox
2. Select "Verify then delete" from dropdown
3. Fill in job details (name, source, dest)
4. Click "Create Job"

**Expected**:
- Job created successfully
- Job has `delete_source_after=True`
- Job has correct `deletion_mode`

**Actual**: ____________________

---

### Test 2.5: Create Job With Deletion Disabled
**Steps**:
1. Leave deletion checkbox unchecked
2. Fill in job details (name, source, dest)
3. Click "Create Job"

**Expected**:
- Job created successfully
- Job has `delete_source_after=False`
- No deletion mode set

**Actual**: ____________________

---

## Task 3: Browser Console Verification

**Action**: Check for JavaScript errors

**Steps**:
1. Open browser DevTools (F12)
2. Go to Console tab
3. Perform Test 2.1-2.3 above
4. Monitor console for errors

**Expected**:
- No JavaScript errors
- HTMX requests visible in Network tab
- Server responds with appropriate HTML fragments

**Validation**:
- [ ] No console errors
- [ ] HTMX requests show `delete_source_after=true` when checked
- [ ] HTMX requests show `delete_source_after=false` when unchecked

---

## Task 4: Network Request Verification

**Action**: Verify HTMX sends correct parameters

**Steps**:
1. Open browser DevTools Network tab
2. Check deletion checkbox
3. Inspect request to `/jobs/deletion-ui`

**Expected Request (Checked)**:
```
GET /jobs/deletion-ui?delete_source_after=true
```

**Steps**:
4. Uncheck deletion checkbox
5. Inspect request to `/jobs/deletion-ui`

**Expected Request (Unchecked)**:
```
GET /jobs/deletion-ui?delete_source_after=false
```

**Validation**:
- [ ] Checked sends `delete_source_after=true`
- [ ] Unchecked sends `delete_source_after=false`
- [ ] No duplicate requests
- [ ] Server returns appropriate HTML

---

## Summary

**Total Tasks**: 4 tasks
- Task 1: Code change (1 file, 3 modifications)
- Task 2: Manual UI testing (5 test cases)
- Task 3: Console verification
- Task 4: Network verification

**Estimated Time**: 10-15 minutes
- Code change: 2 minutes
- Testing: 8-10 minutes
- Verification: 3-5 minutes

**Success Criteria**:
- ✅ No UI flicker when toggling checkbox
- ✅ Deletion options appear/disappear reliably
- ✅ Can create jobs with deletion enabled
- ✅ Can create jobs with deletion disabled
- ✅ No JavaScript errors
- ✅ HTMX sends correct boolean parameter
