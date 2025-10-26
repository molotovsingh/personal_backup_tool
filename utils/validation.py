"""
Validation utilities for backup operations
"""
import shutil
from pathlib import Path
from typing import Tuple


def check_disk_space(path: str, required_bytes: int = 0) -> Tuple[bool, str, int]:
    """
    Check available disk space at a path

    Args:
        path: Path to check (file or directory)
        required_bytes: Minimum required bytes (0 to just check)

    Returns:
        Tuple of (has_space, message, available_bytes)
    """
    try:
        # Get parent directory for the path
        check_path = Path(path)
        if check_path.is_file():
            check_path = check_path.parent
        elif not check_path.exists():
            # If path doesn't exist, check parent
            check_path = check_path.parent

        # Get disk usage
        stat = shutil.disk_usage(str(check_path))
        available = stat.free
        total = stat.total

        # Calculate percentage available
        percent_available = (available / total) * 100

        if required_bytes > 0:
            if available < required_bytes:
                return False, f"Insufficient space: {available / 1024**3:.2f}GB available, {required_bytes / 1024**3:.2f}GB required", available
            else:
                return True, f"Sufficient space: {available / 1024**3:.2f}GB available", available
        else:
            # Check if less than 10% available
            if percent_available < 10:
                return False, f"Low disk space: {available / 1024**3:.2f}GB ({percent_available:.1f}%) available", available
            else:
                return True, f"Disk space OK: {available / 1024**3:.2f}GB ({percent_available:.1f}%) available", available

    except Exception as e:
        return False, f"Error checking disk space: {str(e)}", 0


def validate_source_readable(path: str) -> Tuple[bool, str]:
    """
    Validate that source path exists and is readable

    Args:
        path: Source path to validate

    Returns:
        Tuple of (is_valid, message)
    """
    try:
        path_obj = Path(path)

        if not path_obj.exists():
            return False, f"Source does not exist: {path}"

        if not path_obj.is_dir() and not path_obj.is_file():
            return False, f"Source is not a file or directory: {path}"

        # Try to list directory or read file metadata
        if path_obj.is_dir():
            try:
                list(path_obj.iterdir())
            except PermissionError:
                return False, f"Source directory is not readable: {path}"
        else:
            try:
                path_obj.stat()
            except PermissionError:
                return False, f"Source file is not readable: {path}"

        return True, f"Source is valid and readable"

    except Exception as e:
        return False, f"Error validating source: {str(e)}"


def validate_destination_writable(path: str) -> Tuple[bool, str]:
    """
    Validate that destination is writable or parent exists

    Args:
        path: Destination path to validate

    Returns:
        Tuple of (is_valid, message)
    """
    import uuid

    def test_write_permission(test_dir: Path, location_name: str) -> Tuple[bool, str]:
        """Helper to test write permissions with proper cleanup"""
        # Use unique filename to avoid conflicts
        test_file = test_dir / f'.backup_manager_test_{uuid.uuid4().hex[:8]}'

        try:
            # Remove existing test file if any (cleanup from previous failed runs)
            if test_file.exists():
                try:
                    test_file.unlink()
                except Exception:
                    pass  # Ignore cleanup errors

            # Try to create and remove test file
            test_file.touch()
            test_file.unlink()
            return True, f"{location_name} is writable"

        except PermissionError:
            return False, f"{location_name} is not writable: {test_dir}"
        except OSError as e:
            # Handle "Resource busy" and other OS errors
            if e.errno == 16:  # Resource busy
                # Try to clean up stale test files
                for old_test in test_dir.glob('.backup_manager_test*'):
                    try:
                        old_test.unlink()
                    except Exception:
                        pass
                # Retry once after cleanup
                try:
                    test_file.touch()
                    test_file.unlink()
                    return True, f"{location_name} is writable (after cleanup)"
                except Exception:
                    return False, f"{location_name} may not be writable (resource busy)"
            return False, f"{location_name} write test failed: {str(e)}"
        except Exception as e:
            return False, f"Error testing {location_name}: {str(e)}"
        finally:
            # Ensure cleanup
            try:
                if test_file.exists():
                    test_file.unlink()
            except Exception:
                pass  # Ignore cleanup errors

    try:
        path_obj = Path(path)

        if path_obj.exists():
            # Check if writable
            if path_obj.is_dir():
                return test_write_permission(path_obj, "Destination")
            else:
                # It's a file, check if we can write to parent
                parent = path_obj.parent
                if not parent.exists():
                    return False, f"Destination parent directory does not exist: {parent}"
                return test_write_permission(parent, "Destination parent")
        else:
            # Path doesn't exist, check parent
            parent = path_obj.parent
            if not parent.exists():
                return False, f"Destination parent directory does not exist: {parent}"
            return test_write_permission(parent, "Destination parent")

    except Exception as e:
        return False, f"Error validating destination: {str(e)}"


def estimate_source_size(path: str, quick_check_only: bool = False, max_files_to_scan: int = 1000) -> Tuple[bool, str, int]:
    """
    Estimate total size of source path

    PERFORMANCE NOTE: For large directories (100K+ files), full estimation can take minutes!
    Use quick_check_only=True to skip size estimation for large dirs.

    Args:
        path: Source path to measure
        quick_check_only: If True, only do quick checks and return 0 for large directories
        max_files_to_scan: Maximum number of files to scan before giving up (default 1000)

    Returns:
        Tuple of (success, message, size_in_bytes)
    """
    try:
        path_obj = Path(path)

        if not path_obj.exists():
            return False, "Source does not exist", 0

        if path_obj.is_file():
            size = path_obj.stat().st_size
            return True, f"File size: {size / 1024**3:.2f}GB", size

        # For directories, do a quick check first
        if quick_check_only:
            # Just confirm the directory exists and is readable
            try:
                # Try to list the directory to confirm it's readable
                next(path_obj.iterdir(), None)
                return True, "Directory size check skipped (large directory)", 0
            except (PermissionError, OSError) as e:
                return False, f"Directory not readable: {str(e)}", 0

        # For directories, calculate total size with a limit
        total_size = 0
        file_count = 0

        for item in path_obj.rglob('*'):
            if item.is_file():
                try:
                    total_size += item.stat().st_size
                    file_count += 1

                    # Stop if we've scanned too many files (prevents hanging)
                    if file_count >= max_files_to_scan:
                        # Return estimated size but indicate it's incomplete
                        return True, f"Directory size (estimated, stopped at {file_count} files): >{total_size / 1024**3:.2f}GB", 0

                except (PermissionError, OSError):
                    continue

        return True, f"Directory size: {total_size / 1024**3:.2f}GB ({file_count} files)", total_size

    except Exception as e:
        return False, f"Error estimating size: {str(e)}", 0


def validate_job_before_start(source: str, dest: str, job_type: str) -> Tuple[bool, str]:
    """
    Comprehensive validation before starting a job

    Args:
        source: Source path
        dest: Destination path
        job_type: 'rsync' or 'rclone'

    Returns:
        Tuple of (is_valid, message)
    """
    errors = []

    # For rsync, validate both paths
    if job_type == 'rsync':
        # Validate source
        valid, msg = validate_source_readable(source)
        if not valid:
            errors.append(msg)

        # Validate destination
        valid, msg = validate_destination_writable(dest)
        if not valid:
            errors.append(msg)

        # Check disk space (use quick mode to avoid hanging on large directories)
        # NOTE: We use quick_check_only=True to prevent blocking for minutes on large directories
        # rsync will fail gracefully if it runs out of space during the backup anyway
        success, msg, source_size = estimate_source_size(source, quick_check_only=True)

        # Only check disk space if we got a reliable size estimate
        if success and source_size > 0:
            has_space, space_msg, available = check_disk_space(dest, source_size)
            if not has_space:
                errors.append(space_msg)
        # If size is 0 (quick check or large directory), just verify destination has SOME space
        elif success:
            has_space, space_msg, available = check_disk_space(dest, 0)
            if not has_space:
                errors.append(space_msg)

    # For rclone, only validate source if it's local
    elif job_type == 'rclone':
        if ':' not in source:
            # Local source
            valid, msg = validate_source_readable(source)
            if not valid:
                errors.append(msg)

        if ':' not in dest:
            # Local destination
            valid, msg = validate_destination_writable(dest)
            if not valid:
                errors.append(msg)

    if errors:
        return False, "; ".join(errors)
    else:
        return True, "All validations passed"
