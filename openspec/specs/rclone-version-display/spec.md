# rclone-version-display Specification

## Purpose
TBD - created by archiving change harden-production-quality. Update Purpose after archive.
## Requirements
### Requirement: Settings page SHALL display rclone version string
The system SHALL execute `rclone version` and extract the version number for display in settings page system information.

#### Scenario: Rclone version shows semantic version string
```python
# Given: Rclone is installed at /usr/local/bin/rclone
# When: Settings page loads system information
# Then: Rclone version displays as "v1.65.0" instead of "/usr/local/bin/rclone"

response = client.get('/settings')
html = response.data.decode('utf-8')

assert 'v1.65' in html  # Version string present
assert '/usr/local/bin/rclone' not in html  # Path not shown as version
```

#### Scenario: System extracts version from rclone --version output
```python
# Given: Rclone binary exists
# When: get_rclone_version() is called
rclone_version = get_rclone_version()

# Then: Version string is extracted correctly
assert rclone_version.startswith('v')  # e.g., "v1.65.0"
assert re.match(r'v\d+\.\d+\.\d+', rclone_version)  # Semantic version format
```

### Requirement: Version detection SHALL handle missing rclone gracefully
The system SHALL display "Not installed" when rclone binary is not found or cannot be executed.

#### Scenario: Rclone not installed shows friendly message
```python
# Given: Rclone is not installed (binary not in PATH)
# When: get_rclone_version() is called
rclone_version = get_rclone_version()

# Then: Returns "Not installed"
assert rclone_version == "Not installed"

# And: Settings page displays the message
response = client.get('/settings')
html = response.data.decode('utf-8')
assert 'Not installed' in html
```

#### Scenario: Rclone execution error shows error state
```python
# Given: Rclone binary exists but cannot execute (permissions issue)
# When: get_rclone_version() is called
rclone_version = get_rclone_version()

# Then: Returns error indication
assert rclone_version in ["Not installed", "Error detecting version"]
```

### Requirement: Version check SHALL cache result to avoid repeated calls
The system SHALL cache the rclone version result for the duration of the application runtime to avoid executing `rclone --version` on every settings page load.

#### Scenario: Version check executes once and caches result
```python
# Given: Flask app just started (no cached version)
# When: First settings page load
response1 = client.get('/settings')

# Then: rclone --version executed
# (Can be verified by mocking subprocess.run and checking call count)

# When: Second settings page load
response2 = client.get('/settings')

# Then: Cached version used (no second subprocess call)
# And: Both responses show same version
```

