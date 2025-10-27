# rsync-progress-display Specification

## Purpose
TBD - created by archiving change harden-production-quality. Update Purpose after archive.
## Requirements
### Requirement: Rsync progress SHALL display total bytes transferred and total size
The system SHALL parse rsync output to extract both bytes_transferred and total_bytes, displaying progress as "X MB / Y MB (Z%)".

#### Scenario: Rsync job shows accurate total size during transfer
```python
# Given: Rsync job transferring 100 MB of files
# When: Job is running and progress updates
# Then: Progress shows bytes_transferred and total_bytes
job = manager.get_job('rsync_backup')
assert job['progress']['bytes_transferred'] > 0
assert job['progress']['total_bytes'] == 100 * 1024 * 1024  # 100 MB
assert job['progress']['percent'] == (bytes_transferred / total_bytes) * 100

# And: UI displays "42 MB / 100 MB (42%)" instead of "42 MB / 0 MB"
```

#### Scenario: Rsync parser extracts total size from output
```python
# Given: Rsync output line contains total size info
rsync_output = "  1,234,567  42%   1.23MB/s    0:00:12"

# When: Parser processes the line
progress = rsync_engine._parse_progress_line(rsync_output)

# Then: Total bytes is calculated from percentage
# total_bytes = bytes_transferred / (percent / 100)
assert progress['bytes_transferred'] == 1234567
assert progress['percent'] == 42
assert progress['total_bytes'] == int(1234567 / 0.42)  # ~2.9 MB
```

### Requirement: Total bytes SHALL remain consistent throughout transfer
The system SHALL maintain a consistent total_bytes value once calculated, preventing display flickering.

#### Scenario: Total bytes value persists across progress updates
```python
# Given: Rsync job has calculated total_bytes = 100 MB
job = manager.get_job('test_job')
initial_total = job['progress']['total_bytes']

# When: Multiple progress updates occur
# (Progress updates at 10%, 25%, 50%, 75%)

# Then: Total bytes remains constant
for update in range(4):
    time.sleep(1)  # Wait for updates
    job = manager.get_job('test_job')
    assert job['progress']['total_bytes'] == initial_total
```

### Requirement: Parser SHALL handle rsync output variations
The system SHALL correctly parse progress from both verbose (-v) and info (--info=progress2) rsync output formats.

#### Scenario: Parser handles --info=progress2 format
```python
# Given: Rsync running with --info=progress2
rsync_output = "     52,428,800  25%   10.00MB/s    0:00:15"

# When: Parser processes the line
progress = rsync_engine._parse_progress_line(rsync_output)

# Then: Values extracted correctly
assert progress['bytes_transferred'] == 52428800
assert progress['percent'] == 25
assert progress['speed_bytes'] > 0
```

#### Scenario: Parser handles traditional -v --progress format
```python
# Given: Rsync running with -v --progress
rsync_output = "1,048,576  10%  500.00kB/s    0:00:30"

# When: Parser processes the line
progress = rsync_engine._parse_progress_line(rsync_output)

# Then: Values extracted correctly
assert progress['bytes_transferred'] == 1048576
assert progress['percent'] == 10
```

