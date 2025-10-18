"""
Configuration module for ORAC Core.

Provides centralized access to constants and configuration loading.
"""

from .constants import (
    NetworkConfig,
    ModelConfig,
    CacheConfig,
    PathConfig,
    APIConfig,
    LogConfig
)
from .loader import ConfigLoader
from .legacy import (
    DATA_DIR,
    FAVORITES_PATH,
    MODEL_CONFIGS_PATH,
    DEFAULT_FAVORITES,
    DEFAULT_MODEL_CONFIGS,
    ensure_data_dir,
    load_favorites,
    load_model_configs,
    save_favorites,
    save_model_configs
)

__all__ = [
    'NetworkConfig',
    'ModelConfig',
    'CacheConfig',
    'PathConfig',
    'APIConfig',
    'LogConfig',
    'ConfigLoader',
    'DATA_DIR',
    'FAVORITES_PATH',
    'MODEL_CONFIGS_PATH',
    'DEFAULT_FAVORITES',
    'DEFAULT_MODEL_CONFIGS',
    'ensure_data_dir',
    'load_favorites',
    'load_model_configs',
    'save_favorites',
    'save_model_configs'
]
