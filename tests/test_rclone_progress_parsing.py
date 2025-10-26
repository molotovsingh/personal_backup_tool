"""
Unit tests for rclone progress parsing

Tests the regex patterns and parsing logic in RcloneEngine._parse_progress()
to ensure accurate progress, speed, and ETA calculations.
"""
import pytest
import sys
from pathlib import Path

# Add parent directory to path to import engines
sys.path.insert(0, str(Path(__file__).parent.parent))

from engines.rclone_engine import RcloneEngine


class TestRcloneProgressParsing:
    """Test rclone progress output parsing"""

    def setup_method(self):
        """Create a minimal RcloneEngine instance for testing"""
        self.engine = RcloneEngine(
            source="/tmp/test_source",
            dest="remote:test_dest",
            job_id="test-job-id"
        )

    def test_parse_basic_progress_line(self):
        """Test parsing a typical rclone progress line"""
        line = "Transferred:   	    1.234 MiB / 10.234 MiB, 12%, 2.456 MiB/s, ETA 3s"

        self.engine._parse_progress(line)
        progress = self.engine.get_progress()

        # Check percentage
        assert progress['percent'] == 12

        # Check bytes transferred (1.234 MiB = 1.234 * 1024^2)
        expected_transferred = int(1.234 * 1024 * 1024)
        assert abs(progress['bytes_transferred'] - expected_transferred) < 1000

        # Check total bytes (10.234 MiB)
        expected_total = int(10.234 * 1024 * 1024)
        assert abs(progress['total_bytes'] - expected_total) < 1000

        # Check speed (2.456 MiB/s)
        expected_speed = int(2.456 * 1024 * 1024)
        assert abs(progress['speed_bytes'] - expected_speed) < 1000

        # Check ETA (3 seconds)
        assert progress['eta_seconds'] == 3

    def test_parse_progress_with_gib(self):
        """Test parsing with GiB units"""
        line = "Transferred:   	    5.5 GiB / 100.0 GiB, 5%, 150.0 MiB/s, ETA 10m30s"

        self.engine._parse_progress(line)
        progress = self.engine.get_progress()

        # Check percentage
        assert progress['percent'] == 5

        # Check bytes transferred (5.5 GiB)
        expected_transferred = int(5.5 * 1024 ** 3)
        assert abs(progress['bytes_transferred'] - expected_transferred) < 10000

        # Check total bytes (100.0 GiB)
        expected_total = int(100.0 * 1024 ** 3)
        assert abs(progress['total_bytes'] - expected_total) < 10000

        # Check speed (150.0 MiB/s)
        expected_speed = int(150.0 * 1024 * 1024)
        assert abs(progress['speed_bytes'] - expected_speed) < 1000

        # Check ETA (10m30s = 630 seconds)
        assert progress['eta_seconds'] == 630

    def test_parse_progress_with_kib(self):
        """Test parsing with KiB units (small files)"""
        line = "Transferred:   	    512 KiB / 2048 KiB, 25%, 128 KiB/s, ETA 12s"

        self.engine._parse_progress(line)
        progress = self.engine.get_progress()

        # Check percentage
        assert progress['percent'] == 25

        # Check bytes transferred (512 KiB)
        expected_transferred = 512 * 1024
        assert abs(progress['bytes_transferred'] - expected_transferred) < 100

        # Check total bytes (2048 KiB)
        expected_total = 2048 * 1024
        assert abs(progress['total_bytes'] - expected_total) < 100

        # Check speed (128 KiB/s)
        expected_speed = 128 * 1024
        assert abs(progress['speed_bytes'] - expected_speed) < 100

    def test_parse_progress_with_tib(self):
        """Test parsing with TiB units (very large files)"""
        line = "Transferred:   	    1.5 TiB / 5.0 TiB, 30%, 500 MiB/s, ETA 2h30m"

        self.engine._parse_progress(line)
        progress = self.engine.get_progress()

        # Check percentage
        assert progress['percent'] == 30

        # Check bytes transferred (1.5 TiB)
        expected_transferred = int(1.5 * 1024 ** 4)
        assert abs(progress['bytes_transferred'] - expected_transferred) < 100000

        # Check total bytes (5.0 TiB)
        expected_total = int(5.0 * 1024 ** 4)
        assert abs(progress['total_bytes'] - expected_total) < 100000

        # Check ETA (2h30m = 9000 seconds)
        assert progress['eta_seconds'] == 9000

    def test_parse_progress_eta_complex_format(self):
        """Test parsing complex ETA format (hours, minutes, seconds)"""
        line = "Transferred:   	    100 MiB / 1000 MiB, 10%, 10 MiB/s, ETA 1h2m3s"

        self.engine._parse_progress(line)
        progress = self.engine.get_progress()

        # Check ETA (1h2m3s = 3600 + 120 + 3 = 3723 seconds)
        assert progress['eta_seconds'] == 3723

    def test_parse_progress_eta_minutes_only(self):
        """Test parsing ETA with only minutes"""
        line = "Transferred:   	    50 MiB / 100 MiB, 50%, 5 MiB/s, ETA 10m"

        self.engine._parse_progress(line)
        progress = self.engine.get_progress()

        # Check ETA (10m = 600 seconds)
        assert progress['eta_seconds'] == 600

    def test_parse_progress_eta_hours_only(self):
        """Test parsing ETA with only hours"""
        line = "Transferred:   	    10 GiB / 100 GiB, 10%, 100 MiB/s, ETA 3h"

        self.engine._parse_progress(line)
        progress = self.engine.get_progress()

        # Check ETA (3h = 10800 seconds)
        assert progress['eta_seconds'] == 10800

    def test_parse_progress_eta_seconds_only(self):
        """Test parsing ETA with only seconds"""
        line = "Transferred:   	    90 MiB / 100 MiB, 90%, 50 MiB/s, ETA 2s"

        self.engine._parse_progress(line)
        progress = self.engine.get_progress()

        # Check ETA (2 seconds)
        assert progress['eta_seconds'] == 2

    def test_parse_progress_100_percent(self):
        """Test parsing at 100% completion"""
        line = "Transferred:   	    100 MiB / 100 MiB, 100%, 10 MiB/s, ETA 0s"

        self.engine._parse_progress(line)
        progress = self.engine.get_progress()

        # Check 100% completion
        assert progress['percent'] == 100

        # Check ETA is 0
        assert progress['eta_seconds'] == 0

    def test_parse_progress_metric_units(self):
        """Test parsing with metric units (MB instead of MiB)"""
        line = "Transferred:   	    500 MB / 1000 MB, 50%, 100 MB/s, ETA 5s"

        self.engine._parse_progress(line)
        progress = self.engine.get_progress()

        # Check bytes (500 MB = 500 * 10^6)
        expected_transferred = 500 * 1000 * 1000
        assert abs(progress['bytes_transferred'] - expected_transferred) < 1000

        # Check speed (100 MB/s)
        expected_speed = 100 * 1000 * 1000
        assert abs(progress['speed_bytes'] - expected_speed) < 1000

    def test_parse_progress_multiple_updates(self):
        """Test that progress updates correctly over multiple lines"""
        lines = [
            "Transferred:   	    10 MiB / 100 MiB, 10%, 5 MiB/s, ETA 18s",
            "Transferred:   	    50 MiB / 100 MiB, 50%, 10 MiB/s, ETA 5s",
            "Transferred:   	    90 MiB / 100 MiB, 90%, 15 MiB/s, ETA 1s",
        ]

        for line in lines:
            self.engine._parse_progress(line)

        progress = self.engine.get_progress()

        # Should have the values from the last line
        assert progress['percent'] == 90
        expected_transferred = int(90 * 1024 * 1024)
        assert abs(progress['bytes_transferred'] - expected_transferred) < 1000
        assert progress['eta_seconds'] == 1

    def test_parse_progress_malformed_line_graceful(self):
        """Test that malformed lines don't crash the parser"""
        malformed_lines = [
            "This is not a valid progress line",
            "Transferred: invalid format",
            "",
            "  1,234,567  50%  (to-chk=50/100)",  # rsync format, should be ignored
        ]

        # Get initial progress state
        initial_progress = self.engine.get_progress().copy()

        for line in malformed_lines:
            self.engine._parse_progress(line)

        # Progress should remain unchanged (graceful degradation)
        current_progress = self.engine.get_progress()
        assert current_progress['percent'] == initial_progress['percent']
        assert current_progress['bytes_transferred'] == initial_progress['bytes_transferred']

    def test_parse_progress_varying_whitespace(self):
        """Test parsing with varying whitespace (rclone uses tabs)"""
        lines = [
            "Transferred:   	    1 MiB / 10 MiB, 10%, 1 MiB/s, ETA 9s",  # tabs
            "Transferred:        1 MiB / 10 MiB, 10%, 1 MiB/s, ETA 9s",  # spaces
            "Transferred:	1 MiB / 10 MiB, 10%, 1 MiB/s, ETA 9s",  # single tab
        ]

        for line in lines:
            self.engine._parse_progress(line)
            progress = self.engine.get_progress()

            # All should parse to 10%
            assert progress['percent'] == 10


class TestRcloneSizeParsing:
    """Test rclone size string parsing (_parse_size method)"""

    def setup_method(self):
        """Create a minimal RcloneEngine instance for testing"""
        self.engine = RcloneEngine(
            source="/tmp/test_source",
            dest="remote:test_dest",
            job_id="test-size-parsing"
        )

    def test_parse_size_bytes(self):
        """Test parsing byte sizes"""
        assert self.engine._parse_size("1234 B") == 1234
        assert self.engine._parse_size("0 B") == 0

    def test_parse_size_kib(self):
        """Test parsing KiB sizes"""
        expected = int(1.5 * 1024)
        assert abs(self.engine._parse_size("1.5 KiB") - expected) < 1

        expected = 512 * 1024
        assert self.engine._parse_size("512 KiB") == expected

    def test_parse_size_mib(self):
        """Test parsing MiB sizes"""
        expected = int(2.5 * 1024 * 1024)
        assert abs(self.engine._parse_size("2.5 MiB") - expected) < 10

        expected = 100 * 1024 * 1024
        assert self.engine._parse_size("100 MiB") == expected

    def test_parse_size_gib(self):
        """Test parsing GiB sizes"""
        expected = int(1.5 * 1024 ** 3)
        assert abs(self.engine._parse_size("1.5 GiB") - expected) < 100

        expected = 10 * 1024 ** 3
        assert abs(self.engine._parse_size("10 GiB") - expected) < 100

    def test_parse_size_tib(self):
        """Test parsing TiB sizes"""
        expected = int(1.0 * 1024 ** 4)
        assert abs(self.engine._parse_size("1.0 TiB") - expected) < 1000

        expected = int(0.5 * 1024 ** 4)
        assert abs(self.engine._parse_size("0.5 TiB") - expected) < 1000

    def test_parse_size_metric_units(self):
        """Test parsing metric units (KB, MB, GB, TB)"""
        assert self.engine._parse_size("1 KB") == 1000
        assert self.engine._parse_size("1 MB") == 1000 ** 2
        assert self.engine._parse_size("1 GB") == 1000 ** 3
        assert self.engine._parse_size("1 TB") == 1000 ** 4

    def test_parse_size_decimal_values(self):
        """Test parsing decimal size values"""
        expected = int(1.234 * 1024 * 1024)
        assert abs(self.engine._parse_size("1.234 MiB") - expected) < 10

        expected = int(0.5 * 1024 ** 3)
        assert abs(self.engine._parse_size("0.5 GiB") - expected) < 100

    def test_parse_size_malformed_graceful(self):
        """Test that malformed size strings return 0"""
        assert self.engine._parse_size("invalid") == 0
        assert self.engine._parse_size("") == 0
        assert self.engine._parse_size("123") == 0  # Missing unit
        assert self.engine._parse_size("MiB") == 0  # Missing value


class TestRcloneProgressAccuracy:
    """Test accuracy of rclone progress calculations"""

    def setup_method(self):
        """Create a minimal RcloneEngine instance for testing"""
        self.engine = RcloneEngine(
            source="/tmp/test_source",
            dest="remote:test_dest",
            job_id="test-accuracy"
        )

    def test_percentage_accuracy_exact(self):
        """Ensure percentage is extracted exactly from rclone output"""
        test_cases = [0, 1, 10, 25, 50, 75, 99, 100]

        for expected_percent in test_cases:
            line = f"Transferred:   	    {expected_percent} MiB / 100 MiB, {expected_percent}%, 1 MiB/s, ETA 1s"
            self.engine._parse_progress(line)
            progress = self.engine.get_progress()

            assert progress['percent'] == expected_percent, \
                f"Expected {expected_percent}%, got {progress['percent']}%"

    def test_size_accuracy_within_1_percent(self):
        """Ensure size calculations are accurate within 1%"""
        test_cases = [
            ("1 KiB", 1 * 1024),
            ("1 MiB", 1 * 1024 ** 2),
            ("1 GiB", 1 * 1024 ** 3),
            ("1 TiB", 1 * 1024 ** 4),
            ("2.5 MiB", 2.5 * 1024 ** 2),
            ("0.5 GiB", 0.5 * 1024 ** 3),
        ]

        for size_str, expected_bytes in test_cases:
            result = self.engine._parse_size(size_str)

            # Allow ±1% tolerance for floating point
            tolerance = expected_bytes * 0.01
            assert abs(result - expected_bytes) <= tolerance, \
                f"For {size_str}: expected {expected_bytes} bytes, got {result} bytes"

    def test_speed_accuracy_within_10_percent(self):
        """Ensure speed calculation is accurate within 10%"""
        test_cases = [
            ("1 KiB/s", 1 * 1024),
            ("1 MiB/s", 1 * 1024 ** 2),
            ("1 GiB/s", 1 * 1024 ** 3),
            ("100 MiB/s", 100 * 1024 ** 2),
            ("2.5 MiB/s", 2.5 * 1024 ** 2),
        ]

        for speed_str, expected_bytes in test_cases:
            line = f"Transferred:   	    10 MiB / 100 MiB, 10%, {speed_str}, ETA 1s"
            self.engine._parse_progress(line)
            progress = self.engine.get_progress()

            # Allow ±10% tolerance
            tolerance = expected_bytes * 0.1
            assert abs(progress['speed_bytes'] - expected_bytes) <= tolerance, \
                f"For {speed_str}: expected {expected_bytes} bytes/s, got {progress['speed_bytes']} bytes/s"

    def test_eta_accuracy_exact(self):
        """Ensure ETA calculation is exact (no tolerance needed)"""
        test_cases = [
            ("ETA 0s", 0),
            ("ETA 30s", 30),
            ("ETA 1m", 60),
            ("ETA 5m30s", 330),
            ("ETA 1h", 3600),
            ("ETA 2h30m", 9000),
            ("ETA 1h2m3s", 3723),
        ]

        for eta_str, expected_seconds in test_cases:
            line = f"Transferred:   	    10 MiB / 100 MiB, 10%, 1 MiB/s, {eta_str}"
            self.engine._parse_progress(line)
            progress = self.engine.get_progress()

            assert progress['eta_seconds'] == expected_seconds, \
                f"For {eta_str}: expected {expected_seconds}s, got {progress['eta_seconds']}s"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
