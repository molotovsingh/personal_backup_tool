# Harden Flask Jobs UX

## Why

The deletion checkbox and crash recovery prompt work correctly but lack robustness features for edge cases (rapid toggling, network failures, double-submits) and accessibility improvements. Adding these low-risk enhancements improves resilience and user experience.

## What Changes

Add robustness, accessibility, and UX clarity improvements to Flask jobs page:

1. **Deletion checkbox resilience** - Handle rapid toggles, network errors, and provide visual feedback
2. **Accessibility improvements** - Add ARIA attributes and semantic HTML
3. **Crash recovery UX polish** - Prevent double-submits and add helper text
4. **Tests** - Validate deletion UI partial and crash recovery rendering

## Problem

Current implementation works but has edge case vulnerabilities:

### 1. Rapid Toggle Issues
- **Problem:** Quickly toggling deletion checkbox sends multiple HTMX requests
- **Issue:** Last response may not win deterministically, causing stale UI
- **Evidence:** `flask_app/templates/jobs.html:107` lacks `hx-sync` to drop in-flight requests

### 2. Network Failure Handling
- **Problem:** Network errors leave deletion options in unknown state
- **Issue:** No user feedback when HTMX request fails
- **Evidence:** No `hx-on::request-error` handler present

### 3. Accessibility Gaps
- **Problem:** Deletion radio group lacks semantic markup
- **Issue:** Screen readers can't properly announce form structure
- **Evidence:** `flask_app/templates/partials/deletion_options.html` missing fieldset/legend

### 4. Double-Submit Risk
- **Problem:** Crash recovery buttons can be clicked multiple times
- **Issue:** Could create duplicate recovery attempts
- **Evidence:** `flask_app/templates/base.html` buttons lack disabled-on-click

## Solution

Four targeted improvements (all template-only, no backend changes):

### 1. Deletion Checkbox Robustness
- Add `hx-sync="closest form:drop"` to cancel in-flight requests
- Add `hx-indicator` for loading feedback
- Add `hx-on::request-error` for network failure handling
- Add ARIA attributes for accessibility

### 2. Deletion Options Semantics
- Wrap radio group in `<fieldset>` with `<legend>`
- Improves screen reader navigation

### 3. Crash Recovery Polish
- Add helper text under "Recover" button
- Disable buttons on click to prevent double-submit

### 4. Test Coverage
- Test deletion UI partial returns correct content
- Test crash recovery prompt renders correctly

## Scope

**In Scope:**
- Template modifications (jobs.html, deletion_options.html, base.html)
- HTMX attribute additions (hx-sync, hx-indicator, hx-on::request-error)
- ARIA attributes for accessibility
- Button disable-on-click for crash recovery
- Basic test cases for deletion UI and crash recovery

**Out of Scope:**
- Backend logic changes (routes already handle all cases correctly)
- Complex testing frameworks
- Visual design changes
- New features

## Impact

**Benefits:**
- **Robustness** - Handles rapid toggling and network errors gracefully
- **Accessibility** - Better screen reader experience
- **UX Polish** - Clear feedback, no confusing states
- **Testability** - Validates key UI behaviors

**Risks:**
- Very low - All changes are additive template improvements
- No backend modifications
- HTMX features are well-documented and stable

**User Impact:**
- Smoother deletion configuration (no stale states)
- Better error feedback
- More accessible interface
- Prevents accidental double-clicks on crash recovery

## Files to Modify

### 1. `flask_app/templates/jobs.html`
Add to deletion checkbox:
- `hx-sync="closest form:drop"`
- `hx-indicator=".deletion-options-indicator"`
- `hx-on::request-error="..."`
- `aria-controls`, `aria-expanded` attributes
- Loading indicator span

### 2. `flask_app/templates/partials/deletion_options.html`
Wrap radio group:
- Add `<fieldset>` wrapper
- Add `<legend>` for group label

### 3. `flask_app/templates/base.html`
Update crash recovery buttons:
- Add `onclick="this.disabled=true; this.form.submit();"`
- Add helper text under "Recover" button

### 4. `tests/` (new files)
- `test_deletion_ui_partial.py` - Test GET /jobs/deletion-ui responses
- `test_crash_recovery_prompt.py` - Test crash recovery rendering

## Validation

**Functional:**
- [ ] Rapid checkbox toggling shows loading indicator
- [ ] Network errors display error message
- [ ] Deletion options appear/disappear smoothly
- [ ] Screen readers announce deletion mode properly
- [ ] Crash recovery buttons disable after click
- [ ] Helper text visible under Recover button

**Tests:**
- [ ] `test_deletion_ui_true()` passes
- [ ] `test_deletion_ui_false()` passes
- [ ] `test_crash_recovery_prompt_rendered()` passes
