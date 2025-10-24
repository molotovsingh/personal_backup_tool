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
    try:
        path_obj = Path(path)

        if path_obj.exists():
            # Check if writable
            if path_obj.is_dir():
                # Try to create a test file
                test_file = path_obj / '.backup_manager_test'
                try:
                    test_file.touch()
                    test_file.unlink()
                    return True, "Destination is writable"
                except PermissionError:
                    return False, f"Destination directory is not writable: {path}"
            else:
                # It's a file, check if we can write to parent
                parent = path_obj.parent
                if not parent.exists():
                    return False, f"Destination parent directory does not exist: {parent}"

                test_file = parent / '.backup_manager_test'
                try:
                    test_file.touch()
                    test_file.unlink()
                    return True, "Destination parent is writable"
                except PermissionError:
                    return False, f"Destination parent is not writable: {parent}"
        else:
            # Path doesn't exist, check parent
            parent = path_obj.parent
            if not parent.exists():
                return False, f"Destination parent directory does not exist: {parent}"

            # Try to create test file in parent
            test_file = parent / '.backup_manager_test'
            try:
                test_file.touch()
                test_file.unlink()
                return True, "Destination parent is writable"
            except PermissionError:
                return False, f"Destination parent is not writable: {parent}"

    except Exception as e:
        return False, f"Error validating destination: {str(e)}"


def estimate_source_size(path: str) -> Tuple[bool, str, int]:
    """
    Estimate total size of source path

    Args:
        path: Source path to measure

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

        # For directories, calculate total size
        total_size = 0
        file_count = 0

        for item in path_obj.rglob('*'):
            if item.is_file():
                try:
                    total_size += item.stat().st_size
                    file_count += 1
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

        # Check disk space
        success, msg, source_size = estimate_source_size(source)
        if success and source_size > 0:
            has_space, space_msg, available = check_disk_space(dest, source_size)
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
