"""
Integration tests for source deletion features

Tests cover:
- Safety check utilities
- Deletion logger
- Job model deletion settings
- End-to-end deletion workflows
"""
import os
import tempfile
import shutil
from pathlib import Path
import pytest

from models.job import Job
from utils.safety_checks import (
    validate_deletion_safety,
    estimate_source_size,
    check_destination_space,
    is_cloud_path,
    format_bytes,
    count_files_in_directory
)
from utils.deletion_logger import DeletionLogger


class TestSafetyChecks:
    """Test suite for safety check utilities"""

    def test_is_cloud_path(self):
        """Test cloud path detection"""
        # Cloud paths
        assert is_cloud_path("remote:bucket/path") is True
        assert is_cloud_path("s3:my-bucket") is True
        assert is_cloud_path("gdrive:folder") is True

        # Local paths
        assert is_cloud_path("/local/path") is False
        assert is_cloud_path("./relative/path") is False
        assert is_cloud_path("") is False

        # Windows paths (should not be detected as cloud)
        assert is_cloud_path("C:\\Users\\test") is False
        assert is_cloud_path("D:\\data\\backup") is False

    def test_format_bytes(self):
        """Test byte formatting"""
        assert format_bytes(0) == "0 B"
        assert format_bytes(512) == "512 B"
        assert format_bytes(1024) == "1.00 KB"
        assert format_bytes(1024 * 1024) == "1.00 MB"
        assert format_bytes(1024 * 1024 * 1024) == "1.00 GB"
        assert format_bytes(1024 * 1024 * 1024 * 1024) == "1.00 TB"

    def test_estimate_source_size_file(self):
        """Test source size estimation for a single file"""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            # Write 1KB of data
            tmp.write(b'x' * 1024)
            tmp.flush()
            tmp_path = tmp.name

        try:
            size = estimate_source_size(tmp_path)
            assert size == 1024
        finally:
            os.unlink(tmp_path)

    def test_estimate_source_size_directory(self):
        """Test source size estimation for a directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            file1 = Path(tmpdir) / "file1.txt"
            file2 = Path(tmpdir) / "subdir" / "file2.txt"
            file2.parent.mkdir(parents=True)

            file1.write_bytes(b'x' * 1024)  # 1KB
            file2.write_bytes(b'y' * 2048)  # 2KB

            size = estimate_source_size(tmpdir)
            assert size == 3072  # 3KB total

    def test_estimate_source_size_nonexistent(self):
        """Test source size estimation for nonexistent path"""
        size = estimate_source_size("/nonexistent/path")
        assert size == 0

    def test_count_files_in_directory(self):
        """Test file counting in directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Create test files
            (Path(tmpdir) / "file1.txt").touch()
            (Path(tmpdir) / "file2.txt").touch()
            subdir = Path(tmpdir) / "subdir"
            subdir.mkdir()
            (subdir / "file3.txt").touch()
            (subdir / "file4.txt").touch()

            count = count_files_in_directory(tmpdir)
            assert count == 4

    def test_count_files_single_file(self):
        """Test file counting for single file"""
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp_path = tmp.name

        try:
            count = count_files_in_directory(tmp_path)
            assert count == 1
        finally:
            os.unlink(tmp_path)

    def test_check_destination_space_sufficient(self):
        """Test destination space check with sufficient space"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Request 1KB (should have plenty of space)
            is_safe, msg = check_destination_space(tmpdir, 1024)
            assert is_safe is True
            assert "GB free" in msg

    def test_check_destination_space_cloud_path(self):
        """Test destination space check for cloud paths"""
        is_safe, msg = check_destination_space("remote:bucket", 1024)
        # Should allow with warning for cloud paths
        assert is_safe is True
        assert "cloud" in msg.lower() or "remote" in msg.lower()

    def test_validate_deletion_safety_success(self):
        """Test deletion safety validation with valid paths"""
        with tempfile.TemporaryDirectory() as source_dir:
            with tempfile.TemporaryDirectory() as dest_dir:
                # Create a test file in source
                test_file = Path(source_dir) / "test.txt"
                test_file.write_bytes(b'x' * 1024)

                is_safe, msg = validate_deletion_safety(
                    source_dir,
                    dest_dir,
                    require_space_check=False  # Skip space check for speed
                )
                assert is_safe is True
                assert "passed" in msg.lower()

    def test_validate_deletion_safety_nonexistent_source(self):
        """Test deletion safety validation with nonexistent source"""
        with tempfile.TemporaryDirectory() as dest_dir:
            is_safe, msg = validate_deletion_safety(
                "/nonexistent/source",
                dest_dir,
                require_space_check=False
            )
            assert is_safe is False
            assert "does not exist" in msg

    def test_validate_deletion_safety_empty_source(self):
        """Test deletion safety validation with empty source"""
        with tempfile.TemporaryDirectory() as source_dir:
            with tempfile.TemporaryDirectory() as dest_dir:
                # Empty source directory
                is_safe, msg = validate_deletion_safety(
                    source_dir,
                    dest_dir,
                    require_space_check=False
                )
                assert is_safe is False
                assert "empty" in msg.lower() or "Cannot estimate" in msg


class TestDeletionLogger:
    """Test suite for deletion logger"""

    def test_logger_initialization(self):
        """Test deletion logger initialization"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # Override log directory for testing
            job_id = "test-job-123"
            logger = DeletionLogger(job_id)

            # Logger should be created without errors
            assert logger.job_id == job_id

    def test_log_deletion_start(self):
        """Test logging deletion start"""
        with tempfile.TemporaryDirectory() as tmpdir:
            job_id = "test-job-123"
            logger = DeletionLogger(job_id)

            logger.log_deletion_start(mode='verify_then_delete', total_files=10)

            # Check log file was created
            log_file = Path.home() / "backup-manager" / "logs" / f"deletions_{job_id}.log"
            assert log_file.exists()

            # Check log contains expected content
            content = log_file.read_text()
            assert "DELETION STARTED" in content
            assert "verify_then_delete" in content

    def test_log_deletion(self):
        """Test logging individual file deletion"""
        import uuid
        job_id = f"test-job-deletion-{uuid.uuid4()}"
        logger = DeletionLogger(job_id)

        logger.log_deletion_start(mode='per_file', total_files=5)
        logger.log_deletion("/test/file1.txt", file_size=1024)
        logger.log_deletion("/test/file2.txt", file_size=2048)

        # Check deletion count
        assert logger.get_deletion_count() == 2

        # Check total bytes
        assert logger.get_total_bytes_deleted() == 3072

    def test_log_deletion_complete(self):
        """Test logging deletion completion"""
        job_id = "test-job-789"
        logger = DeletionLogger(job_id)

        logger.log_deletion_start(mode='verify_then_delete', total_files=3)
        logger.log_deletion("/test/file1.txt", file_size=1024)
        logger.log_deletion("/test/file2.txt", file_size=2048)
        logger.log_deletion_complete(files_deleted=2, bytes_deleted=3072, errors=0)

        # Check log file content
        log_file = Path.home() / "backup-manager" / "logs" / f"deletions_{job_id}.log"
        content = log_file.read_text()

        assert "DELETION COMPLETED" in content
        assert "2" in content  # Files deleted count
        assert "3.00 KB" in content

    def test_log_verification(self):
        """Test logging verification start and result"""
        job_id = "test-job-verify"
        logger = DeletionLogger(job_id)

        logger.log_deletion_start(mode='verify_then_delete', total_files=5)
        logger.log_verification_start()
        logger.log_verification_result(passed=True, details="All files verified")

        # Check log file content
        log_file = Path.home() / "backup-manager" / "logs" / f"deletions_{job_id}.log"
        content = log_file.read_text()

        assert "VERIFICATION STARTED" in content
        assert "VERIFICATION PASSED" in content
        assert "All files verified" in content

    def test_log_verification_failure(self):
        """Test logging verification failure"""
        job_id = "test-job-verify-fail"
        logger = DeletionLogger(job_id)

        logger.log_deletion_start(mode='verify_then_delete', total_files=5)
        logger.log_verification_start()
        logger.log_verification_result(passed=False, details="3 files do not match")

        # Check log file content
        log_file = Path.home() / "backup-manager" / "logs" / f"deletions_{job_id}.log"
        content = log_file.read_text()

        assert "VERIFICATION FAILED" in content
        assert "3 files do not match" in content

    def test_get_deletion_log(self):
        """Test retrieving deletion log entries"""
        job_id = "test-job-retrieve"
        logger = DeletionLogger(job_id)

        logger.log_deletion_start(mode='per_file', total_files=2)
        logger.log_deletion("/test/file1.txt", file_size=1024)
        logger.log_deletion("/test/file2.txt", file_size=2048)

        # Get deletion log
        log_entries = logger.get_deletion_log(limit=10)

        # Should have entries
        assert len(log_entries) > 0

        # Check entry structure (deletion logs return file_path, size, etc.)
        for entry in log_entries:
            assert 'timestamp' in entry
            # Deletion log entries have file_path instead of message
            assert 'file_path' in entry or 'size' in entry


class TestJobDeletionSettings:
    """Test suite for Job model deletion settings"""

    def test_job_default_deletion_settings(self):
        """Test job is created with deletion disabled by default"""
        job = Job(
            name="Test Job",
            source="/test/source",
            dest="/test/dest",
            job_type="rsync"
        )

        assert job.delete_source_after is False
        assert job.deletion_mode == 'verify_then_delete'
        assert job.deletion_confirmed is False
        assert job.skip_deletion_this_run is False

    def test_job_enable_deletion(self):
        """Test enabling deletion on a job"""
        job = Job(
            name="Test Job",
            source="/test/source",
            dest="/test/dest",
            job_type="rsync"
        )

        job.enable_deletion(mode='verify_then_delete', confirmed=True)

        assert job.delete_source_after is True
        assert job.deletion_mode == 'verify_then_delete'
        assert job.deletion_confirmed is True

    def test_job_enable_deletion_per_file(self):
        """Test enabling per-file deletion mode"""
        job = Job(
            name="Test Job",
            source="/test/source",
            dest="/test/dest",
            job_type="rsync"
        )

        job.enable_deletion(mode='per_file', confirmed=True)

        assert job.delete_source_after is True
        assert job.deletion_mode == 'per_file'

    def test_job_enable_deletion_invalid_mode(self):
        """Test enabling deletion with invalid mode raises error"""
        job = Job(
            name="Test Job",
            source="/test/source",
            dest="/test/dest",
            job_type="rsync"
        )

        with pytest.raises(ValueError, match="Invalid deletion mode"):
            job.enable_deletion(mode='invalid_mode', confirmed=True)

    def test_job_disable_deletion(self):
        """Test disabling deletion on a job"""
        job = Job(
            name="Test Job",
            source="/test/source",
            dest="/test/dest",
            job_type="rsync"
        )

        # Enable first
        job.enable_deletion(mode='verify_then_delete', confirmed=True)
        assert job.delete_source_after is True

        # Then disable
        job.disable_deletion()
        assert job.delete_source_after is False
        assert job.skip_deletion_this_run is False

    def test_job_should_delete_source(self):
        """Test should_delete_source logic"""
        job = Job(
            name="Test Job",
            source="/test/source",
            dest="/test/dest",
            job_type="rsync"
        )

        # Disabled by default
        assert job.should_delete_source() is False

        # Enable deletion
        job.enable_deletion(mode='verify_then_delete', confirmed=True)
        assert job.should_delete_source() is True

        # Skip for this run
        job.settings['skip_deletion_this_run'] = True
        assert job.should_delete_source() is False

    def test_job_deletion_settings_serialization(self):
        """Test deletion settings survive serialization"""
        job = Job(
            name="Test Job",
            source="/test/source",
            dest="/test/dest",
            job_type="rsync"
        )

        job.enable_deletion(mode='per_file', confirmed=True)

        # Convert to dict
        job_dict = job.to_dict()

        # Recreate from dict
        restored_job = Job.from_dict(job_dict)

        # Check deletion settings preserved
        assert restored_job.delete_source_after is True
        assert restored_job.deletion_mode == 'per_file'
        assert restored_job.deletion_confirmed is True


class TestDeletionIntegration:
    """Integration tests for deletion workflows"""

    def test_job_creation_with_deletion(self):
        """Test creating a job with deletion settings"""
        settings = {
            'delete_source_after': True,
            'deletion_mode': 'verify_then_delete',
            'deletion_confirmed': True
        }

        job = Job(
            name="Test Deletion Job",
            source="/test/source",
            dest="/test/dest",
            job_type="rsync",
            settings=settings
        )

        assert job.delete_source_after is True
        assert job.deletion_mode == 'verify_then_delete'
        assert job.should_delete_source() is True

    def test_deletion_with_skip_flag(self):
        """Test deletion can be skipped for individual runs"""
        settings = {
            'delete_source_after': True,
            'deletion_mode': 'verify_then_delete',
            'deletion_confirmed': True,
            'skip_deletion_this_run': False
        }

        job = Job(
            name="Test Skip Job",
            source="/test/source",
            dest="/test/dest",
            job_type="rsync",
            settings=settings
        )

        # Should delete initially
        assert job.should_delete_source() is True

        # Set skip flag
        job.settings['skip_deletion_this_run'] = True
        assert job.should_delete_source() is False

        # Clear skip flag
        job.settings['skip_deletion_this_run'] = False
        assert job.should_delete_source() is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
