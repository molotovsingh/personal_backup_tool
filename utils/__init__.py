"""
Utilities package for Backup Manager
"""
from .rclone_helper import (
    is_rclone_installed,
    list_remotes,
    is_remote_configured,
    get_config_instructions
)

__all__ = [
    'is_rclone_installed',
    'list_remotes',
    'is_remote_configured',
    'get_config_instructions'
]
