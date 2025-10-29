## Why
Users want all deletion-related UI elements present as soon as the Create Job form opens. Hiding the controls until a checkbox is toggled and interrupting submission with a browser alert creates friction and confusion.

## What Changes
- Default the form to deletion enabled on initial render; show all deletion controls immediately.
- Remove blocking browser alert; rely on inline or server validation for the required confirmation.
- Keep default deletion mode as `verify_then_delete` with prominent warnings.
- Preserve ability to uncheck the deletion toggle to hide controls without flicker.
- Update `deletion-ui-controls` spec to reflect default-visible behavior and a no-alert rule.

## Impact
- Affected specs: `deletion-ui-controls` (MODIFIED)
- Affected implementation (later PR):
  - `fastapi_app/templates/jobs.html` (default checked, initial render of deletion options, remove before-request alert)
  - `fastapi_app/templates/partials/deletion_options.html` (no change expected)
  - `fastapi_app/routers/jobs.py` (no change expected)
  - tests touching deletion UI behavior

## Non-Goals
- No changes to backend deletion semantics, job execution, or safety checks.
- No changes to rsync/rclone engines.

## Risks / Mitigations
- Risk: Defaulting deletion to ON is inherently destructive.
  - Mitigation: Confirmation remains required; warnings remain prominent; default mode is verify-then-delete.
- Risk: Users who do not want deletion may be surprised by default visibility.
  - Mitigation: Deletion toggle remains; unchecking hides options smoothly.

## Rollback Plan
Revert to the previous behavior (checkbox unchecked by default, options hidden until toggled, remove the default-visible scenarios from the spec).

## Open Questions
1. Should the Create Job button be disabled until the confirmation checkbox is checked when deletion is ON?
2. Should the UI remember the last-used deletion preference per user/session?

## Acceptance Criteria
- On opening the Create Job form, deletion controls are visible, defaulted to `verify_then_delete`, with the confirmation checkbox present.
- No browser alert or modal is used for validation; failures are inline or via server flash message.
- Unchecking the deletion toggle hides the controls; rechecking shows them; no flicker.
- Tests assert initial visibility and server-side refusal when confirmation is missing.

