"""
Safety Checks - Pre-deletion validation utilities

Provides safety checks before allowing source file deletion to prevent data loss.
"""
import os
import shutil
from pathlib import Path
from typing import Tuple


def check_destination_space(dest_path: str, required_bytes: int) -> Tuple[bool, str]:
    """
    Verify destination has enough free space

    Args:
        dest_path: Destination directory path
        required_bytes: Minimum required free space in bytes

    Returns:
        Tuple of (is_safe, message)
        - is_safe: True if destination has enough space, False otherwise
        - message: Explanation of the result
    """
    try:
        dest = Path(dest_path)

        # Handle cloud/rclone paths (remote:path format)
        if ':' in dest_path and not dest_path.startswith('/'):
            # This is likely a cloud path (e.g., "remote:bucket/path")
            # We cannot check cloud storage space, so warn user
            return (
                True,  # Allow but warn
                "⚠️ Cannot verify cloud storage space - ensure destination has enough capacity"
            )

        # Ensure destination directory exists (or can be created)
        if not dest.exists():
            # Check parent directory space instead
            parent = dest.parent
            if not parent.exists():
                return False, f"Destination parent directory does not exist: {parent}"
            dest = parent

        # Get filesystem stats
        stats = shutil.disk_usage(dest)
        free_bytes = stats.free
        free_gb = free_bytes / (1024**3)
        required_gb = required_bytes / (1024**3)

        # Calculate safety margin (require 10% extra space)
        safety_margin = required_bytes * 1.1
        min_free_bytes = safety_margin

        if free_bytes < min_free_bytes:
            return (
                False,
                f"Insufficient destination space: {free_gb:.2f} GB free, "
                f"need {required_gb:.2f} GB + 10% margin = {min_free_bytes / 1024**3:.2f} GB"
            )

        # All good!
        return (
            True,
            f"✅ Destination has {free_gb:.2f} GB free (need {required_gb:.2f} GB)"
        )

    except Exception as e:
        # If we can't check, be conservative and block deletion
        return False, f"Error checking destination space: {str(e)}"


def estimate_source_size(source_path: str) -> int:
    """
    Calculate total size of files in source directory

    Args:
        source_path: Source directory path

    Returns:
        Total size in bytes (0 if error or empty)
    """
    try:
        source = Path(source_path)

        if not source.exists():
            return 0

        if source.is_file():
            # Single file source
            return source.stat().st_size

        # Directory source - walk and sum all files
        total_bytes = 0
        for item in source.rglob('*'):
            if item.is_file():
                try:
                    total_bytes += item.stat().st_size
                except (OSError, PermissionError):
                    # Skip files we can't access
                    continue

        return total_bytes

    except Exception as e:
        print(f"Warning: Failed to estimate source size: {e}")
        return 0


def validate_deletion_safety(
    source_path: str,
    dest_path: str,
    require_space_check: bool = True
) -> Tuple[bool, str]:
    """
    Comprehensive safety validation before allowing deletion

    Args:
        source_path: Source directory path
        dest_path: Destination directory path (can be local or cloud remote)
        require_space_check: If True, require space check to pass (skipped for cloud)

    Returns:
        Tuple of (is_safe, message)
    """
    try:
        source = Path(source_path)

        # Check 1: Source must exist
        if not source.exists():
            return False, f"Source path does not exist: {source_path}"

        # Check 2: Source and dest must not be the same
        # (Only check for local paths - cloud paths can't be resolved)
        if not is_cloud_path(dest_path):
            try:
                dest = Path(dest_path)
                if source.resolve() == dest.resolve():
                    return False, "Source and destination are the same - cannot delete!"
            except Exception:
                # Resolution might fail, skip this check
                pass

        # Check 3: Estimate source size
        source_bytes = estimate_source_size(source_path)
        if source_bytes == 0:
            return False, "Cannot estimate source size (empty or inaccessible)"

        source_gb = source_bytes / (1024**3)

        # Check 4: Destination space (if required AND destination is local)
        if require_space_check and not is_cloud_path(dest_path):
            space_ok, space_msg = check_destination_space(dest_path, source_bytes)
            if not space_ok:
                return False, space_msg
        elif is_cloud_path(dest_path):
            # Cloud destination - skip space check with warning
            return (
                True,
                f"✅ Safety checks passed (source: {source_gb:.2f} GB) - "
                f"⚠️ Cloud destination '{dest_path}' - ensure remote has enough space"
            )

        # All checks passed (local destination)
        return (
            True,
            f"✅ Safety checks passed (source: {source_gb:.2f} GB)"
        )

    except Exception as e:
        return False, f"Safety validation error: {str(e)}"


def is_cloud_path(path: str) -> bool:
    """
    Check if a path is a cloud/remote path (rclone format)

    Args:
        path: Path to check

    Returns:
        True if path looks like a cloud path (e.g., "remote:bucket/path")
    """
    # Rclone remote paths have format "remote:path"
    # Local paths start with / or C:\ (Windows)
    if not path:
        return False

    # Check for rclone remote format
    if ':' in path:
        # Not a cloud path if it's a Windows drive (C:\) or starts with /
        if path.startswith('/') or (len(path) > 1 and path[1] == ':' and path[0].isalpha() and len(path) > 2 and path[2] in ['\\', '/']):
            return False
        return True

    return False


def format_bytes(bytes_count: int) -> str:
    """
    Format bytes into human-readable string

    Args:
        bytes_count: Number of bytes

    Returns:
        Formatted string (e.g., "1.5 GB")
    """
    if bytes_count >= 1024**4:
        return f"{bytes_count / 1024**4:.2f} TB"
    elif bytes_count >= 1024**3:
        return f"{bytes_count / 1024**3:.2f} GB"
    elif bytes_count >= 1024**2:
        return f"{bytes_count / 1024**2:.2f} MB"
    elif bytes_count >= 1024:
        return f"{bytes_count / 1024:.2f} KB"
    else:
        return f"{bytes_count} B"


def count_files_in_directory(dir_path: str) -> int:
    """
    Count total number of files in a directory (recursively)

    Args:
        dir_path: Directory path

    Returns:
        Number of files (0 if error)
    """
    try:
        path = Path(dir_path)
        if not path.exists():
            return 0

        if path.is_file():
            return 1

        count = 0
        for item in path.rglob('*'):
            if item.is_file():
                count += 1

        return count

    except Exception as e:
        print(f"Warning: Failed to count files: {e}")
        return 0
