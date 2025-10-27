# Deletion Mode Options

**ID**: `deletion-mode-options`
**Created**: 2025-10-26
**Updated**: 2025-10-26

## Overview

The deletion mode options allow users to choose between "verify then delete" (safest) and "per-file deletion" modes. This spec ensures the radio group uses semantic HTML for proper screen reader navigation.

## ADDED Requirements

### Requirement: Semantic radio group structure

**ID**: `REQ-deletion-mode-001`

Deletion mode radio options MUST be wrapped in a fieldset with legend for proper form semantics and accessibility.

**Why**: Screen readers need semantic markup to announce radio groups as a cohesive unit with a clear label.

**Acceptance Criteria**:
- Radio options wrapped in `<fieldset>` element
- Group label uses `<legend>` element (not `<label>`)
- Screen readers announce "Deletion Mode" as the group label
- Radio group structure follows HTML5 best practices
- Visual styling remains unchanged

#### Scenario: Screen reader announces radio group label

**Given** screen reader is active
**And** deletion options are visible
**When** user navigates to deletion mode radio group
**Then** screen reader announces "Deletion Mode" as the group label
**And** radio options are announced as part of the group

#### Scenario: HTML5 validation passes

**Given** deletion options partial is rendered
**When** HTML is validated against HTML5 spec
**Then** fieldset/legend structure validates without errors
**And** radio inputs are properly nested within fieldset

#### Scenario: Visual styling remains consistent

**Given** deletion options are visible
**When** fieldset wrapper is applied
**Then** visual appearance matches pre-fieldset layout
**And** spacing, colors, and fonts are unchanged
**And** responsive behavior works correctly
