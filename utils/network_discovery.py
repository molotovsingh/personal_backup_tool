"""
Network Discovery Utility

Discovers network shares and mounted volumes for easy backup source/destination selection.
Supports both already-mounted volumes and active network scanning for SMB shares.
"""

import os
import subprocess
from pathlib import Path
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


def get_mounted_volumes() -> List[Dict[str, str]]:
    """
    Get list of currently mounted volumes (network shares and external drives).

    Returns:
        List of dicts with keys: name, path, type, size_info
    """
    volumes = []
    volumes_dir = Path("/Volumes")

    if not volumes_dir.exists():
        return volumes

    try:
        # Iterate through /Volumes directory
        for item in volumes_dir.iterdir():
            if item.is_dir() and item.name != "Macintosh HD":
                # Get mount info using df
                # Use -P for POSIX output format (more consistent parsing)
                try:
                    result = subprocess.run(
                        ["df", "-Ph", str(item)],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )

                    if result.returncode == 0:
                        lines = result.stdout.strip().split('\n')
                        if len(lines) >= 2:
                            parts = lines[1].split()
                            filesystem = parts[0] if len(parts) > 0 else "unknown"
                            size = parts[1] if len(parts) > 1 else "?"
                            used = parts[2] if len(parts) > 2 else "?"
                            avail = parts[3] if len(parts) > 3 else "?"

                            # Determine type based on filesystem
                            if filesystem.startswith("//"):
                                vol_type = "smb"
                            elif filesystem.startswith("afp://"):
                                vol_type = "afp"
                            elif filesystem.startswith("/dev/disk"):
                                vol_type = "local"
                            else:
                                vol_type = "network"

                            volumes.append({
                                'name': item.name,
                                'path': str(item),
                                'type': vol_type,
                                'size': size,
                                'used': used,
                                'available': avail,
                                'filesystem': filesystem
                            })
                except subprocess.TimeoutExpired:
                    logger.warning(f"Timeout getting info for {item}")
                    # Still add it, just without size info
                    volumes.append({
                        'name': item.name,
                        'path': str(item),
                        'type': 'unknown',
                        'size': '?',
                        'used': '?',
                        'available': '?',
                        'filesystem': '?'
                    })
                except Exception as e:
                    logger.warning(f"Error getting info for {item}: {e}")
                    continue

    except Exception as e:
        logger.error(f"Error listing volumes: {e}")

    return volumes


def discover_smb_shares(timeout: int = 10) -> List[Dict[str, str]]:
    """
    Discover SMB/CIFS shares on the local network using smbutil.
    This can take several seconds to complete.

    Args:
        timeout: Maximum seconds to wait for discovery

    Returns:
        List of dicts with keys: name, address, type
    """
    discovered = []

    try:
        # Method 1: Try smbutil lookup (macOS specific)
        try:
            result = subprocess.run(
                ["smbutil", "lookup", "*"],
                capture_output=True,
                text=True,
                timeout=timeout
            )

            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    # Parse smbutil output
                    # Format is typically: "NAME (IP_ADDRESS)"
                    if line.strip() and '(' in line:
                        try:
                            name_part = line.split('(')[0].strip()
                            addr_part = line.split('(')[1].split(')')[0].strip()

                            discovered.append({
                                'name': name_part,
                                'address': addr_part,
                                'type': 'smb',
                                'status': 'discovered'
                            })
                        except (IndexError, ValueError, AttributeError) as e:
                            logger.debug(f"Failed to parse SMB discovery line '{line}': {e}")
                            continue
        except subprocess.TimeoutExpired:
            logger.warning("SMB discovery timed out")
        except FileNotFoundError:
            logger.info("smbutil not found, trying alternative method")
        except Exception as e:
            logger.warning(f"Error with smbutil: {e}")

        # Method 2: Try dns-sd (Bonjour/mDNS - works on macOS)
        if not discovered:
            try:
                result = subprocess.run(
                    ["dns-sd", "-B", "_smb._tcp", "local"],
                    capture_output=True,
                    text=True,
                    timeout=min(timeout, 5)  # dns-sd can hang, limit timeout
                )

                # dns-sd outputs continuously, parse what we got
                lines = result.stdout.strip().split('\n')
                for line in lines:
                    if 'Add' in line and '_smb._tcp' in line:
                        # Parse dns-sd output
                        # Format: timestamp Add <number> <domain> _smb._tcp <name>
                        parts = line.split()
                        if len(parts) >= 6:
                            name = ' '.join(parts[5:])
                            discovered.append({
                                'name': name,
                                'address': 'auto',  # Bonjour will resolve
                                'type': 'smb',
                                'status': 'discovered'
                            })
            except subprocess.TimeoutExpired:
                logger.info("dns-sd discovery timed out (this is normal)")
            except FileNotFoundError:
                logger.info("dns-sd not found")
            except Exception as e:
                logger.warning(f"Error with dns-sd: {e}")

    except Exception as e:
        logger.error(f"Error discovering SMB shares: {e}")

    return discovered


def get_all_network_shares(scan_network: bool = False, timeout: int = 10) -> Dict[str, List[Dict[str, str]]]:
    """
    Get comprehensive list of network shares including mounted and optionally discovered.

    Args:
        scan_network: Whether to actively scan network (takes time)
        timeout: Timeout for network scan in seconds

    Returns:
        Dict with keys 'mounted' and 'discovered', each containing list of shares
    """
    result = {
        'mounted': [],
        'discovered': []
    }

    # Always get mounted volumes (fast)
    result['mounted'] = get_mounted_volumes()

    # Optionally scan network (slow)
    if scan_network:
        result['discovered'] = discover_smb_shares(timeout=timeout)

    return result


def list_directory(path: str, show_hidden: bool = False) -> List[Dict[str, any]]:
    """
    List contents of a directory for file browser.

    Args:
        path: Path to list
        show_hidden: Whether to show hidden files (starting with .)

    Returns:
        List of dicts with keys: name, path, is_dir, size
    """
    items = []

    try:
        path_obj = Path(path)

        if not path_obj.exists():
            return items

        if not path_obj.is_dir():
            return items

        # List directory contents
        for item in sorted(path_obj.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
            # Skip hidden files unless requested
            if not show_hidden and item.name.startswith('.'):
                continue

            try:
                # Get size for files
                size_str = ""
                if item.is_file():
                    size = item.stat().st_size
                    if size > 1024**3:
                        size_str = f"{size / 1024**3:.1f} GB"
                    elif size > 1024**2:
                        size_str = f"{size / 1024**2:.1f} MB"
                    elif size > 1024:
                        size_str = f"{size / 1024:.1f} KB"
                    else:
                        size_str = f"{size} B"

                items.append({
                    'name': item.name,
                    'path': str(item),
                    'is_dir': item.is_dir(),
                    'size': size_str,
                    'readable': os.access(str(item), os.R_OK)
                })
            except Exception as e:
                logger.warning(f"Error getting info for {item}: {e}")
                continue

    except PermissionError:
        logger.warning(f"Permission denied: {path}")
    except Exception as e:
        logger.error(f"Error listing directory {path}: {e}")

    return items


def get_home_directory() -> str:
    """Get user's home directory path."""
    return str(Path.home())


def get_common_locations() -> List[Dict[str, str]]:
    """
    Get list of common backup locations for quick access.

    Returns:
        List of dicts with keys: name, path, icon
    """
    home = Path.home()
    locations = [
        {'name': 'Home', 'path': str(home), 'icon': '🏠'},
        {'name': 'Desktop', 'path': str(home / 'Desktop'), 'icon': '🖥️'},
        {'name': 'Documents', 'path': str(home / 'Documents'), 'icon': '📄'},
        {'name': 'Downloads', 'path': str(home / 'Downloads'), 'icon': '⬇️'},
        {'name': 'Pictures', 'path': str(home / 'Pictures'), 'icon': '🖼️'},
        {'name': 'Movies', 'path': str(home / 'Movies'), 'icon': '🎬'},
        {'name': 'Music', 'path': str(home / 'Music'), 'icon': '🎵'},
    ]

    # Only return locations that exist
    return [loc for loc in locations if Path(loc['path']).exists()]
