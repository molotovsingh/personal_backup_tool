"""
Rclone configuration helper utilities
"""
import subprocess
import shutil
import re
from typing import List, Tuple


def is_rclone_installed() -> Tuple[bool, str]:
    """
    Check if rclone is installed and accessible

    Returns:
        Tuple of (is_installed, path_or_error_message)
    """
    rclone_path = shutil.which('rclone')
    if rclone_path:
        return True, rclone_path
    else:
        return False, "rclone not found in PATH. Install with: brew install rclone"


def list_remotes() -> List[str]:
    """
    List all configured rclone remotes

    Returns:
        List of remote names (empty list if rclone not installed or no remotes)
    """
    try:
        # Check if rclone is installed
        is_installed, _ = is_rclone_installed()
        if not is_installed:
            return []

        # Run rclone listremotes command
        result = subprocess.run(
            ['rclone', 'listremotes'],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode != 0:
            return []

        # Parse output - each line is a remote name ending with ":"
        remotes = []
        for line in result.stdout.strip().split('\n'):
            if line.strip():
                # Remove trailing colon
                remote = line.strip().rstrip(':')
                remotes.append(remote)

        return remotes

    except Exception as e:
        import logging
        logging.error(f"Error listing remotes: {e}")
        return []


def is_remote_configured(remote_name: str) -> bool:
    """
    Check if a specific rclone remote is configured

    Args:
        remote_name: Name of the remote to check

    Returns:
        True if remote exists, False otherwise
    """
    remotes = list_remotes()
    return remote_name in remotes


def get_config_instructions() -> str:
    """
    Get step-by-step instructions for configuring rclone

    Returns:
        Formatted instructions string
    """
    is_installed, path_or_msg = is_rclone_installed()

    if not is_installed:
        return f"""
rclone is not installed!

Installation:
  macOS:    brew install rclone
  Linux:    curl https://rclone.org/install.sh | sudo bash
  Windows:  Download from https://rclone.org/downloads/

After installing, run:
  rclone config

Then follow the prompts to configure your cloud storage.
"""

    remotes = list_remotes()
    if not remotes:
        return f"""
rclone is installed at: {path_or_msg}

No remotes configured yet.

To configure a remote (e.g., Google Drive):

1. Run this command in your terminal:
   rclone config

2. Choose 'n' for new remote

3. Give it a name (e.g., 'gdrive')

4. Choose the storage type (e.g., 'drive' for Google Drive)

5. Follow the prompts to authenticate

6. Test with:
   rclone lsd <remote-name>:

For detailed guides, visit: https://rclone.org/docs/
"""

    remotes_list = "\n".join(f"  - {r}" for r in remotes)
    return f"""
rclone is installed at: {path_or_msg}

Configured remotes:
{remotes_list}

To add more remotes, run:
  rclone config

To test a remote:
  rclone lsd <remote-name>:

For detailed guides, visit: https://rclone.org/docs/
"""


def test_remote(remote_name: str) -> Tuple[bool, str]:
    """
    Test if a remote is accessible

    Args:
        remote_name: Name of the remote to test

    Returns:
        Tuple of (success, message)
    """
    try:
        is_installed, msg = is_rclone_installed()
        if not is_installed:
            return False, msg

        if not is_remote_configured(remote_name):
            return False, f"Remote '{remote_name}' is not configured"

        # Try to list root directory
        result = subprocess.run(
            ['rclone', 'lsd', f'{remote_name}:'],
            capture_output=True,
            text=True,
            timeout=10
        )

        if result.returncode == 0:
            return True, f"Remote '{remote_name}' is accessible"
        else:
            error = result.stderr.strip()
            return False, f"Failed to access remote: {error}"

    except subprocess.TimeoutExpired:
        return False, "Remote test timed out"
    except Exception as e:
        return False, f"Error testing remote: {str(e)}"


# Module-level cache for rclone version
_rclone_version_cache = None


def get_rclone_version() -> str:
    """
    Get the installed rclone version string.

    Returns version in format "v1.65.0" or "Not installed" if rclone is not found.
    The result is cached for the lifetime of the application to avoid repeated subprocess calls.

    Returns:
        Version string (e.g., "v1.65.0") or "Not installed"
    """
    global _rclone_version_cache

    # Return cached version if available
    if _rclone_version_cache is not None:
        return _rclone_version_cache

    try:
        # Check if rclone is installed
        is_installed, _ = is_rclone_installed()
        if not is_installed:
            _rclone_version_cache = "Not installed"
            return _rclone_version_cache

        # Execute rclone version command
        result = subprocess.run(
            ['rclone', 'version'],
            capture_output=True,
            text=True,
            timeout=5
        )

        if result.returncode != 0:
            _rclone_version_cache = "Error detecting version"
            return _rclone_version_cache

        # Parse version from first line of output
        # Format: "rclone v1.65.0"
        first_line = result.stdout.strip().split('\n')[0]
        version_match = re.search(r'v\d+\.\d+\.\d+', first_line)

        if version_match:
            _rclone_version_cache = version_match.group()
        else:
            # Fallback: try to extract any version-like string
            _rclone_version_cache = first_line.split()[-1] if first_line else "Unknown"

        return _rclone_version_cache

    except FileNotFoundError:
        _rclone_version_cache = "Not installed"
        return _rclone_version_cache
    except subprocess.TimeoutExpired:
        _rclone_version_cache = "Timeout"
        return _rclone_version_cache
    except Exception as e:
        _rclone_version_cache = f"Error: {str(e)}"
        return _rclone_version_cache
