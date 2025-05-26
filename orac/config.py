"""
orac.config
-----------
Configuration management for ORAC.

Handles loading and initialization of configuration files:
- favorites.json: User's favorite models and settings
- model_configs.yaml: Model-specific configurations
"""

import os
import json
import yaml
from pathlib import Path
from typing import Dict, Any, Optional

from orac.logger import get_logger

logger = get_logger(__name__)

# Default paths
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
FAVORITES_PATH = os.path.join(DATA_DIR, "favorites.json")
MODEL_CONFIGS_PATH = os.path.join(DATA_DIR, "model_configs.yaml")

# Default configurations
DEFAULT_FAVORITES = {
    "favorite_models": [],
    "default_model": None,
    "default_settings": {
        "temperature": 0.7,
        "top_p": 0.7,
        "top_k": 40,
        "max_tokens": 512
    }
}

DEFAULT_MODEL_CONFIGS = {
    "models": {
        "Qwen3-0.6B-Q4_K_M.gguf": {
            "description": "Qwen 3 0.6B Chat Model",
            "context_size": 2048,
            "prompt_format": {
                "template": "<|im_start|>system\n{system_prompt}\n<|im_end|>\n<|im_start|>user\n{user_prompt}\n<|im_end|>\n<|im_start|>assistant\n",
                "system_role": "system",
                "user_role": "user",
                "assistant_role": "assistant"
            },
            "recommended_settings": {
                "temperature": 0.7,
                "top_p": 0.7,
                "top_k": 40,
                "max_tokens": 512
            }
        },
        "Qwen3-1.7B-Q4_K_M.gguf": {
            "description": "Qwen 3 1.7B Chat Model",
            "context_size": 2048,
            "prompt_format": {
                "template": "<|im_start|>system\n{system_prompt}\n<|im_end|>\n<|im_start|>user\n{user_prompt}\n<|im_end|>\n<|im_start|>assistant\n",
                "system_role": "system",
                "user_role": "user",
                "assistant_role": "assistant"
            },
            "recommended_settings": {
                "temperature": 0.7,
                "top_p": 0.7,
                "top_k": 40,
                "max_tokens": 512
            }
        },
        "tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf": {
            "description": "TinyLlama 1.1B Chat Model",
            "context_size": 2048,
            "prompt_format": {
                "template": "<|system|>\n{system_prompt}\n<|user|>\n{user_prompt}\n<|assistant|>\n",
                "system_role": "system",
                "user_role": "user",
                "assistant_role": "assistant"
            },
            "system_prompt": "Input: turn off kitchen lights\nOutput: {\"device\":\"lights\",\"action\":\"off\",\"location\":\"kitchen\"}\n\nInput: set living room thermostat to 70\nOutput: {\"device\":\"thermostat\",\"action\":\"set\",\"location\":\"living room\"}\n\nInput: open bedroom blinds\nOutput: {\"device\":\"blinds\",\"action\":\"open\",\"location\":\"bedroom\"}\n\nInput:",
            "recommended_settings": {
                "temperature": 0.05,
                "top_p": 0.1,
                "top_k": 5,
                "max_tokens": 50
            }
        },
        "distilgpt2.Q2_K.gguf": {
            "description": "DistilGPT2 Base Model",
            "context_size": 1024,
            "prompt_format": {
                "template": "{system_prompt}\n\n{user_prompt}",
                "system_role": "instruction",
                "user_role": "input",
                "assistant_role": "output"
            },
            "recommended_settings": {
                "temperature": 0.7,
                "top_p": 0.9,
                "top_k": 50,
                "max_tokens": 256
            }
        }
    }
}

def ensure_data_dir() -> None:
    """Ensure the data directory exists with correct permissions."""
    os.makedirs(DATA_DIR, exist_ok=True)
    os.chmod(DATA_DIR, 0o755)
    logger.info(f"Ensured data directory exists at {DATA_DIR}")

def load_favorites() -> Dict[str, Any]:
    """
    Load favorites configuration, creating default if missing.
    
    Returns:
        Dictionary containing favorites configuration
    """
    ensure_data_dir()
    
    if not os.path.exists(FAVORITES_PATH):
        logger.info("Creating default favorites.json")
        with open(FAVORITES_PATH, 'w') as f:
            json.dump(DEFAULT_FAVORITES, f, indent=2)
        return DEFAULT_FAVORITES
    
    try:
        with open(FAVORITES_PATH, 'r') as f:
            config = json.load(f)
            # Handle legacy format (list of model names)
            if isinstance(config, list):
                logger.info("Converting legacy favorites format to new format")
                config = {
                    "favorite_models": config,
                    "default_model": config[0] if config else None,
                    "default_settings": DEFAULT_FAVORITES["default_settings"]
                }
                # Save in new format
                with open(FAVORITES_PATH, 'w') as f:
                    json.dump(config, f, indent=2)
            return config
    except Exception as e:
        logger.error(f"Error loading favorites.json: {e}")
        return DEFAULT_FAVORITES

def load_model_configs() -> Dict[str, Any]:
    """
    Load model configurations, creating default if missing.
    
    Returns:
        Dictionary containing model configurations
    """
    ensure_data_dir()
    
    if not os.path.exists(MODEL_CONFIGS_PATH):
        logger.info("Creating default model_configs.yaml")
        with open(MODEL_CONFIGS_PATH, 'w') as f:
            yaml.dump(DEFAULT_MODEL_CONFIGS, f, default_flow_style=False)
        return DEFAULT_MODEL_CONFIGS
    
    try:
        with open(MODEL_CONFIGS_PATH, 'r') as f:
            config = yaml.safe_load(f)
        return config
    except Exception as e:
        logger.error(f"Error loading model_configs.yaml: {e}")
        return DEFAULT_MODEL_CONFIGS

def save_favorites(config: Dict[str, Any]) -> None:
    """
    Save favorites configuration.
    
    Args:
        config: Configuration dictionary to save
    """
    ensure_data_dir()
    try:
        with open(FAVORITES_PATH, 'w') as f:
            json.dump(config, f, indent=2)
        logger.info("Saved favorites.json")
    except Exception as e:
        logger.error(f"Error saving favorites.json: {e}")

def save_model_configs(config: Dict[str, Any]) -> None:
    """
    Save model configurations.
    
    Args:
        config: Configuration dictionary to save
    """
    ensure_data_dir()
    try:
        with open(MODEL_CONFIGS_PATH, 'w') as f:
            yaml.dump(config, f, default_flow_style=False)
        logger.info("Saved model_configs.yaml")
    except Exception as e:
        logger.error(f"Error saving model_configs.yaml: {e}") 