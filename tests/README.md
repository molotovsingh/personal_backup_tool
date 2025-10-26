# Backup Manager Test Suite

This directory contains comprehensive tests for the Backup Manager application, focusing on progress tracking accuracy and UX validation.

## Test Structure

```
tests/
├── __init__.py
├── README.md (this file)
├── pytest.ini (configuration)
├── test_rsync_progress_parsing.py
├── test_rclone_progress_parsing.py
└── fixtures/
    ├── __init__.py
    └── test_data_generator.py
```

## Running Tests

### Run All Tests
```bash
uv run pytest tests/ -v
```

### Run Specific Test File
```bash
uv run pytest tests/test_rsync_progress_parsing.py -v
uv run pytest tests/test_rclone_progress_parsing.py -v
```

### Run Specific Test Class
```bash
uv run pytest tests/test_rsync_progress_parsing.py::TestRsyncProgressParsing -v
```

### Run Specific Test
```bash
uv run pytest tests/test_rsync_progress_parsing.py::TestRsyncProgressParsing::test_parse_basic_progress_line -v
```

### Run with Coverage (if pytest-cov is installed)
```bash
uv pip install pytest-cov
uv run pytest tests/ --cov=. --cov-report=html
```

## Test Categories

### Unit Tests (Current)

**test_rsync_progress_parsing.py** (16 tests)
- Tests rsync progress output parsing
- Validates percentage, speed, ETA accuracy
- Edge cases: large files, special characters, malformed input
- Accuracy targets:
  - Percentage: ±1%
  - Speed: ±10%
  - ETA: exact

**test_rclone_progress_parsing.py** (25 tests)
- Tests rclone progress output parsing
- Validates size parsing (B, KiB, MiB, GiB, TiB)
- Tests metric vs binary units
- Accuracy targets:
  - Percentage: exact
  - Size: ±1%
  - Speed: ±10%
  - ETA: exact

### Test Fixtures

**test_data_generator.py**
- Creates test files and directories
- Supports various scenarios: small files, large files, mixed datasets
- Includes backup verification utilities
- Methods for simulating partial transfers and corrupted files

Example usage:
```python
from tests.fixtures.test_data_generator import create_test_scenario

# Create a mixed dataset
gen = create_test_scenario('mixed')
print(f"Source: {gen.source_dir}")
print(f"Total files: {gen.get_file_count()}")
print(f"Total size: {gen.get_total_size() / 1024 / 1024:.2f} MB")

# Clean up when done
gen.cleanup()
```

## Test Results

Last run: All 41 tests passing (0.15s)

```
test_rclone_progress_parsing.py  25 passed
test_rsync_progress_parsing.py   16 passed
================== 41 passed in 0.15s ==================
```

## Future Test Development

### Integration Tests (Planned)
- Real backup operations with test data
- Progress tracking over actual transfers
- Network interruption simulation
- Resume functionality validation

### E2E Tests (Planned)
- Full workflow: create job → start → monitor → complete
- UI state validation
- Multi-job concurrent operations
- Settings persistence

### Manual Test Checklist (Planned)
- Visual UX validation
- Progress bar smoothness
- ETA display clarity
- Error message usability

## Accuracy Targets

Based on test validation:

| Metric | Target | Current |
|--------|--------|---------|
| Progress % | ±1% | ✅ Passing |
| Transfer Speed | ±10% | ✅ Passing |
| ETA | Exact | ✅ Passing |
| Size Parsing | ±1% | ✅ Passing |

## Adding New Tests

1. Create test file: `tests/test_your_feature.py`
2. Import necessary modules
3. Create test classes with `Test` prefix
4. Add test methods with `test_` prefix
5. Run pytest to validate

Example:
```python
import pytest
from your_module import YourClass

class TestYourFeature:
    def setup_method(self):
        self.instance = YourClass()

    def test_basic_functionality(self):
        result = self.instance.do_something()
        assert result == expected_value
```

## Pytest Configuration

See `pytest.ini` for:
- Test discovery patterns
- Output formatting
- Logging configuration
- Custom markers

## Dependencies

- pytest >= 7.4.0

Install with:
```bash
uv pip install -r requirements.txt
```
