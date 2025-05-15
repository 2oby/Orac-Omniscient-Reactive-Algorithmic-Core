"""
orac.model_config
----------------
Manages model configurations functionality.
"""

import yaml
from pathlib import Path
from typing import Dict, Optional
from orac.logger import get_logger
from orac.models import ModelConfigs, ModelConfig, ModelSettings

logger = get_logger(__name__)

# Store configs in a YAML file in the app directory
CONFIG_FILE = Path("/app/data/model_configs.yaml")

def ensure_config_dir():
    """Ensure the config directory exists."""
    CONFIG_FILE.parent.mkdir(parents=True, exist_ok=True)

def load_configs() -> ModelConfigs:
    """Load model configurations from YAML file."""
    try:
        ensure_config_dir()
        if CONFIG_FILE.exists():
            with open(CONFIG_FILE, 'r') as f:
                data = yaml.safe_load(f) or {}
                return ModelConfigs(**data)
        # Return default config if file doesn't exist
        return ModelConfigs(
            defaults=ModelSettings(),
            models={}
        )
    except Exception as e:
        logger.error(f"Error loading model configs: {e}")
        return ModelConfigs(
            defaults=ModelSettings(),
            models={}
        )

def save_configs(configs: ModelConfigs):
    """Save model configurations to YAML file."""
    try:
        ensure_config_dir()
        with open(CONFIG_FILE, 'w') as f:
            yaml.safe_dump(configs.dict(), f, default_flow_style=False, sort_keys=False)
    except Exception as e:
        logger.error(f"Error saving model configs: {e}")
        raise

def get_model_config(model_name: str) -> Optional[ModelConfig]:
    """Get configuration for a specific model."""
    configs = load_configs()
    return configs.models.get(model_name)

def update_model_config(model_name: str, config: ModelConfig) -> bool:
    """Update configuration for a specific model."""
    try:
        configs = load_configs()
        configs.models[model_name] = config
        save_configs(configs)
        return True
    except Exception as e:
        logger.error(f"Error updating model config for {model_name}: {e}")
        return False

def delete_model_config(model_name: str) -> bool:
    """Delete configuration for a specific model."""
    try:
        configs = load_configs()
        if model_name in configs.models:
            del configs.models[model_name]
            save_configs(configs)
            return True
        return False
    except Exception as e:
        logger.error(f"Error deleting model config for {model_name}: {e}")
        return False

def get_default_settings() -> ModelSettings:
    """Get default model settings."""
    return load_configs().defaults

def update_default_settings(settings: ModelSettings) -> bool:
    """Update default model settings."""
    try:
        configs = load_configs()
        configs.defaults = settings
        save_configs(configs)
        return True
    except Exception as e:
        logger.error(f"Error updating default settings: {e}")
        return False 