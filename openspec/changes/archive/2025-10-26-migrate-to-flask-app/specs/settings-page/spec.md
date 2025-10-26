# Spec: Settings Page

## ADDED Requirements

### Requirement: Settings page displays application configuration form

The settings page SHALL display a form with all application settings (defaults, intervals, retry attempts) and allow users to update values.

#### Scenario: Settings form displays all configuration

**Given** the user navigates to the settings page
**When** the page loads
**Then** a form displays all settings:
  - Default bandwidth limit (KB/s)
  - Auto-start on launch (checkbox)
  - Network check interval (seconds)
  - Max retry attempts
  - Dashboard auto-refresh interval (seconds)
**And** current values are pre-filled from settings.yaml
**And** each field has a label and help text

#### Scenario: Save settings updates configuration file

**Given** the user modifies setting values
**When** the user clicks "Save Settings"
**Then** HTMX sends POST request to `/settings/save`
**And** Flask validates the new values
**And** settings.yaml is updated with new values
**And** success message is displayed
**And** form remains on page (no redirect)

#### Scenario: Reset settings to defaults

**Given** the user wants to restore default values
**When** the user clicks "Reset to Defaults"
**Then** confirmation dialog is shown
**And** if confirmed, settings are reset to default values
**And** settings.yaml is updated
**And** form fields are updated to show default values
**And** success message is displayed

### Requirement: Settings page displays system information

The settings page SHALL display read-only system information including data directory paths and tool installation status.

#### Scenario: System info displays paths

**Given** the settings page is loaded
**When** system information section is rendered
**Then** the following paths are displayed:
  - Jobs storage path (jobs.yaml location)
  - Settings storage path (settings.yaml location)
  - Logs directory path
**And** paths are displayed as read-only text
**And** paths are absolute (not relative)

#### Scenario: Tool check displays installation status

**Given** the settings page is loaded
**When** the tool check section is rendered
**Then** rsync installation status is checked and displayed
**And** rclone installation status is checked and displayed
**And** each tool shows: name, installed (yes/no), version (if installed)
**And** if tool is missing, installation instructions are shown
