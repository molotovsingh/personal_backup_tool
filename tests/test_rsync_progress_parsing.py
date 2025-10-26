"""
Unit tests for rsync progress parsing

Tests the regex patterns and parsing logic in RsyncEngine._parse_progress()
to ensure accurate progress, speed, and ETA calculations.
"""
import pytest
import sys
from pathlib import Path

# Add parent directory to path to import engines
sys.path.insert(0, str(Path(__file__).parent.parent))

from engines.rsync_engine import RsyncEngine


class TestRsyncProgressParsing:
    """Test rsync progress output parsing"""

    def setup_method(self):
        """Create a minimal RsyncEngine instance for testing"""
        self.engine = RsyncEngine(
            source="/tmp/test_source",
            dest="/tmp/test_dest",
            job_id="test-job-id"
        )

    def test_parse_basic_progress_line(self):
        """Test parsing a typical rsync progress line"""
        line = "  1,234,567,890  45%   2.34MB/s    0:01:23 (xfr#9, to-chk=123/456)"

        self.engine._parse_progress(line)
        progress = self.engine.get_progress()

        # Check percentage calculation from to-chk
        # to-chk=123/456 means 456 total, 123 remaining → 333 done → 73% complete
        assert progress['percent'] == 73, f"Expected 73%, got {progress['percent']}%"

        # Check bytes transferred
        assert progress['bytes_transferred'] == 1234567890

        # Check speed (2.34 MB/s = 2.34 * 1024 * 1024 bytes)
        expected_speed = int(2.34 * 1024 * 1024)
        assert abs(progress['speed_bytes'] - expected_speed) < 100, \
            f"Speed mismatch: expected ~{expected_speed}, got {progress['speed_bytes']}"

        # Check ETA (0:01:23 = 83 seconds)
        assert progress['eta_seconds'] == 83

    def test_parse_progress_without_to_chk(self):
        """Test parsing progress line without to-chk (older rsync versions)"""
        line = "  5,678,901,234  67%   10.5MB/s    0:05:42"

        self.engine._parse_progress(line)
        progress = self.engine.get_progress()

        # Should still parse bytes, speed, and ETA
        assert progress['bytes_transferred'] == 5678901234

        expected_speed = int(10.5 * 1024 * 1024)
        assert abs(progress['speed_bytes'] - expected_speed) < 100

        assert progress['eta_seconds'] == 5 * 60 + 42

    def test_parse_progress_kb_speed(self):
        """Test parsing with KB/s speed (small files)"""
        line = "  12,345  89%   123.45kB/s    0:00:05 (to-chk=1/10)"

        self.engine._parse_progress(line)
        progress = self.engine.get_progress()

        # Check KB/s conversion
        expected_speed = int(123.45 * 1024)
        assert abs(progress['speed_bytes'] - expected_speed) < 10

        # Check percentage (10 total, 1 remaining = 9 done = 90%)
        assert progress['percent'] == 90

    def test_parse_progress_gb_speed(self):
        """Test parsing with GB/s speed (very fast transfers)"""
        line = "  987,654,321,098  99%   1.5GB/s    0:00:01 (to-chk=1/100)"

        self.engine._parse_progress(line)
        progress = self.engine.get_progress()

        # Check GB/s conversion
        expected_speed = int(1.5 * 1024 * 1024 * 1024)
        assert abs(progress['speed_bytes'] - expected_speed) < 1000

        # Check percentage (100 total, 1 remaining = 99 done = 99%)
        assert progress['percent'] == 99

    def test_parse_progress_long_eta(self):
        """Test parsing with long ETA (hours)"""
        line = "  100,000,000  5%   500kB/s    2:30:45 (to-chk=950/1000)"

        self.engine._parse_progress(line)
        progress = self.engine.get_progress()

        # Check ETA (2:30:45 = 2*3600 + 30*60 + 45 = 9045 seconds)
        assert progress['eta_seconds'] == 9045

        # Check percentage (1000 total, 950 remaining = 50 done = 5%)
        assert progress['percent'] == 5

    def test_parse_progress_completion(self):
        """Test parsing when transfer is nearly complete"""
        line = "  999,999,999  100%   5.0MB/s    0:00:00 (to-chk=0/1000)"

        self.engine._parse_progress(line)
        progress = self.engine.get_progress()

        # Check 100% completion (1000 total, 0 remaining = 100%)
        assert progress['percent'] == 100

        # Check ETA is 0
        assert progress['eta_seconds'] == 0

    def test_parse_progress_single_file(self):
        """Test parsing with single file transfer"""
        line = "  50,000  50%   1.0MB/s    0:00:01 (to-chk=0/1)"

        self.engine._parse_progress(line)
        progress = self.engine.get_progress()

        # Single file: 1 total, 0 remaining = 100%
        assert progress['percent'] == 100

    def test_parse_progress_many_files(self):
        """Test parsing with many files (stress test for integer handling)"""
        line = "  1,000,000,000,000  25%   100MB/s    1:00:00 (to-chk=7500/10000)"

        self.engine._parse_progress(line)
        progress = self.engine.get_progress()

        # 10000 total, 7500 remaining = 2500 done = 25%
        assert progress['percent'] == 25

        # Check large byte count
        assert progress['bytes_transferred'] == 1000000000000

    def test_parse_progress_no_commas_in_bytes(self):
        """Test parsing when bytes don't have comma separators"""
        line = "  123456789  50%   2MB/s    0:01:00 (to-chk=50/100)"

        self.engine._parse_progress(line)
        progress = self.engine.get_progress()

        # Should handle both comma and non-comma formats
        assert progress['bytes_transferred'] == 123456789
        assert progress['percent'] == 50

    def test_parse_progress_edge_case_zero_speed(self):
        """Test parsing when speed is very low/zero"""
        line = "  1000  1%   0.01kB/s    9:59:59 (to-chk=99/100)"

        self.engine._parse_progress(line)
        progress = self.engine.get_progress()

        # Should still parse correctly
        assert progress['percent'] == 1
        expected_speed = int(0.01 * 1024)
        assert progress['speed_bytes'] == expected_speed

    def test_parse_progress_multiple_updates(self):
        """Test that progress updates correctly over multiple lines"""
        lines = [
            "  100,000  10%   1MB/s    0:00:10 (to-chk=900/1000)",
            "  500,000  50%   2MB/s    0:00:05 (to-chk=500/1000)",
            "  900,000  90%   3MB/s    0:00:01 (to-chk=100/1000)",
        ]

        for line in lines:
            self.engine._parse_progress(line)

        progress = self.engine.get_progress()

        # Should have the values from the last line
        assert progress['percent'] == 90
        assert progress['bytes_transferred'] == 900000
        expected_speed = int(3 * 1024 * 1024)
        assert abs(progress['speed_bytes'] - expected_speed) < 100
        assert progress['eta_seconds'] == 1

    def test_parse_progress_malformed_line_graceful(self):
        """Test that malformed lines don't crash the parser"""
        malformed_lines = [
            "This is not a valid progress line",
            "  invalid  format  here",
            "",
            "Transferred: 123 bytes",  # rclone format, should be ignored
        ]

        # Get initial progress state
        initial_progress = self.engine.get_progress().copy()

        for line in malformed_lines:
            self.engine._parse_progress(line)

        # Progress should remain unchanged (graceful degradation)
        current_progress = self.engine.get_progress()
        assert current_progress['percent'] == initial_progress['percent']
        assert current_progress['bytes_transferred'] == initial_progress['bytes_transferred']

    def test_parse_progress_special_characters_in_filename(self):
        """Test parsing when filenames contain special characters"""
        # rsync shows filenames, but our parser ignores them - just validate it doesn't crash
        line = "  1,000,000  50%   1MB/s    0:00:01 (to-chk=50/100)"
        filename_line = "My File (with parentheses) [and brackets].txt"

        self.engine._parse_progress(filename_line)  # Should be ignored
        self.engine._parse_progress(line)  # Should parse correctly

        progress = self.engine.get_progress()
        assert progress['percent'] == 50


class TestRsyncProgressAccuracy:
    """Test accuracy of rsync progress calculations"""

    def setup_method(self):
        """Create a minimal RsyncEngine instance for testing"""
        self.engine = RsyncEngine(
            source="/tmp/test_source",
            dest="/tmp/test_dest",
            job_id="test-job-accuracy"
        )

    def test_percentage_accuracy_within_1_percent(self):
        """Ensure percentage calculation is accurate within 1%"""
        test_cases = [
            ("to-chk=0/100", 100),    # 100% complete
            ("to-chk=50/100", 50),    # 50% complete
            ("to-chk=99/100", 1),     # 1% complete
            ("to-chk=1/1000", 99),    # 999/1000 = 99.9% ≈ 99%
            ("to-chk=500/1000", 50),  # 50% complete
        ]

        for check_str, expected_percent in test_cases:
            line = f"  1000000  {expected_percent}%   1MB/s    0:00:01 ({check_str})"
            self.engine._parse_progress(line)
            progress = self.engine.get_progress()

            # Allow ±1% tolerance for integer rounding
            assert abs(progress['percent'] - expected_percent) <= 1, \
                f"For {check_str}: expected {expected_percent}%, got {progress['percent']}%"

    def test_speed_accuracy_within_10_percent(self):
        """Ensure speed calculation is accurate within 10%"""
        test_cases = [
            ("1kB/s", 1 * 1024),
            ("1MB/s", 1 * 1024 * 1024),
            ("1GB/s", 1 * 1024 * 1024 * 1024),
            ("2.5MB/s", 2.5 * 1024 * 1024),
            ("0.5GB/s", 0.5 * 1024 * 1024 * 1024),
        ]

        for speed_str, expected_bytes in test_cases:
            line = f"  1000000  50%   {speed_str}    0:00:01 (to-chk=50/100)"
            self.engine._parse_progress(line)
            progress = self.engine.get_progress()

            # Allow ±10% tolerance
            tolerance = expected_bytes * 0.1
            assert abs(progress['speed_bytes'] - expected_bytes) <= tolerance, \
                f"For {speed_str}: expected {expected_bytes} bytes/s, got {progress['speed_bytes']} bytes/s"

    def test_eta_accuracy_exact(self):
        """Ensure ETA calculation is exact (no tolerance needed for time parsing)"""
        test_cases = [
            ("0:00:00", 0),
            ("0:00:30", 30),
            ("0:01:00", 60),
            ("0:05:30", 330),
            ("1:00:00", 3600),
            ("2:30:45", 9045),
        ]

        for eta_str, expected_seconds in test_cases:
            line = f"  1000000  50%   1MB/s    {eta_str} (to-chk=50/100)"
            self.engine._parse_progress(line)
            progress = self.engine.get_progress()

            assert progress['eta_seconds'] == expected_seconds, \
                f"For {eta_str}: expected {expected_seconds}s, got {progress['eta_seconds']}s"


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
