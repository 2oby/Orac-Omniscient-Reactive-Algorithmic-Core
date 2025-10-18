"""
Configuration loader for ORAC Core.

Handles loading configuration from multiple sources with precedence:
1. Environment variables (highest priority)
2. Configuration files (YAML, JSON)
3. Default constants (lowest priority)
"""

import os
import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
import logging

from .constants import NetworkConfig, ModelConfig, PathConfig

logger = logging.getLogger(__name__)


class ConfigLoader:
    """Unified configuration loader."""

    def __init__(self, data_dir: Optional[str] = None):
        """Initialize the config loader.

        Args:
            data_dir: Base directory for configuration files
        """
        self.data_dir = Path(data_dir) if data_dir else Path(PathConfig.DATA_DIR)
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def get_ha_url(self) -> str:
        """Get Home Assistant URL.

        Precedence: HA_URL env var > default
        """
        return os.getenv('HA_URL', f'http://{NetworkConfig.DEFAULT_HA_HOST}:{NetworkConfig.DEFAULT_HA_PORT}')

    def get_ha_token(self) -> str:
        """Get Home Assistant API token.

        Precedence: HA_TOKEN env var > empty string
        """
        return os.getenv('HA_TOKEN', '')

    def get_orac_port(self) -> int:
        """Get ORAC API port.

        Precedence: ORAC_PORT env var > default
        """
        return int(os.getenv('ORAC_PORT', str(NetworkConfig.DEFAULT_ORAC_PORT)))

    def get_models_path(self) -> str:
        """Get models directory path.

        Precedence: ORAC_MODELS_PATH env var > default
        """
        return os.getenv('ORAC_MODELS_PATH', PathConfig.MODELS_DIR)

    def get_data_dir(self) -> str:
        """Get data directory path.

        Precedence: DATA_DIR env var > default
        """
        return os.getenv('DATA_DIR', str(self.data_dir))

    def load_json_config(self, filename: str) -> Dict[str, Any]:
        """Load a JSON configuration file.

        Args:
            filename: Name of the JSON file (relative to data_dir)

        Returns:
            Configuration dictionary
        """
        filepath = self.data_dir / filename

        if not filepath.exists():
            logger.warning(f"Config file not found: {filepath}")
            return {}

        try:
            with open(filepath, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to load JSON config {filepath}: {e}")
            return {}

    def load_yaml_config(self, filename: str) -> Dict[str, Any]:
        """Load a YAML configuration file.

        Args:
            filename: Name of the YAML file (relative to data_dir)

        Returns:
            Configuration dictionary
        """
        filepath = self.data_dir / filename

        if not filepath.exists():
            logger.warning(f"Config file not found: {filepath}")
            return {}

        try:
            with open(filepath, 'r') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logger.error(f"Failed to load YAML config {filepath}: {e}")
            return {}

    def save_json_config(self, filename: str, data: Dict[str, Any]) -> bool:
        """Save a JSON configuration file.

        Args:
            filename: Name of the JSON file (relative to data_dir)
            data: Configuration data to save

        Returns:
            True if successful
        """
        filepath = self.data_dir / filename

        try:
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved config to {filepath}")
            return True
        except Exception as e:
            logger.error(f"Failed to save JSON config {filepath}: {e}")
            return False

    def save_yaml_config(self, filename: str, data: Dict[str, Any]) -> bool:
        """Save a YAML configuration file.

        Args:
            filename: Name of the YAML file (relative to data_dir)
            data: Configuration data to save

        Returns:
            True if successful
        """
        filepath = self.data_dir / filename

        try:
            with open(filepath, 'w') as f:
                yaml.dump(data, f, default_flow_style=False)
            logger.info(f"Saved config to {filepath}")
            return True
        except Exception as e:
            logger.error(f"Failed to save YAML config {filepath}: {e}")
            return False
