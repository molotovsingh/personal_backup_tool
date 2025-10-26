"""
Settings manager for Backup Manager application
"""
import yaml
from pathlib import Path
from typing import Any, Dict
from core.paths import get_settings_file


class Settings:
    """Manages application settings with YAML persistence"""

    DEFAULT_SETTINGS = {
        'default_bandwidth_limit': 0,  # 0 = unlimited
        'auto_start_on_launch': False,
        'network_check_interval': 30,  # seconds
        'max_retry_attempts': 10,
        'auto_refresh_interval': 2,  # seconds for dashboard
        'verification_mode': 'fast',  # 'fast' (size/time), 'checksum' (hash), or 'verify_after' (verify after sync)
    }

    def __init__(self, settings_path: str = None):
        """
        Initialize Settings

        Args:
            settings_path: Path to settings file (defaults to configured data directory)
        """
        if settings_path:
            self.settings_path = Path(settings_path)
        else:
            self.settings_path = get_settings_file()

        # Ensure directory exists
        self.settings_path.parent.mkdir(parents=True, exist_ok=True)

        # Load or create settings
        self._settings = self._load()

    def _load(self) -> Dict[str, Any]:
        """Load settings from file or create with defaults"""
        if self.settings_path.exists():
            try:
                with open(self.settings_path, 'r') as f:
                    settings = yaml.safe_load(f)
                    if settings:
                        # Merge with defaults (in case new settings were added)
                        return {**self.DEFAULT_SETTINGS, **settings}
            except Exception as e:
                print(f"Error loading settings: {e}")

        # Return defaults if file doesn't exist or error
        return self.DEFAULT_SETTINGS.copy()

    def _save(self):
        """Save current settings to file"""
        try:
            with open(self.settings_path, 'w') as f:
                yaml.safe_dump(self._settings, f, default_flow_style=False)
        except Exception as e:
            print(f"Error saving settings: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get a setting value

        Args:
            key: Setting key
            default: Default value if key not found

        Returns:
            Setting value or default
        """
        return self._settings.get(key, default)

    def set(self, key: str, value: Any):
        """
        Set a setting value

        Args:
            key: Setting key
            value: Setting value
        """
        self._settings[key] = value
        self._save()

    def get_all(self) -> Dict[str, Any]:
        """Get all settings"""
        return self._settings.copy()

    def reset_to_defaults(self):
        """Reset all settings to defaults"""
        self._settings = self.DEFAULT_SETTINGS.copy()
        self._save()


# Global singleton
_settings_instance = None


def get_settings() -> Settings:
    """Get the global Settings singleton"""
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = Settings()
    return _settings_instance
