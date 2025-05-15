"""
orac.model_config
----------------
Manages model configurations functionality.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Optional, Any
from orac.logger import get_logger
from orac.models import ModelConfigs, ModelConfig, ModelSettings, ModelType, ModelCapability

logger = get_logger(__name__)

CONFIG_DIR = "/app/data"
CONFIG_FILE = os.path.join(CONFIG_DIR, "model_configs.yaml")

def ensure_config_dir():
    """Ensure the configuration directory exists."""
    os.makedirs(CONFIG_DIR, exist_ok=True)

def get_default_settings() -> ModelSettings:
    """Get default model settings."""
    return ModelSettings(
        temperature=0.7,
        max_tokens=2048,
        top_p=0.95,
        repeat_penalty=1.1,
        top_k=40
    )

def create_model_config(model_name: str) -> ModelConfig:
    """Create a new model configuration with default settings."""
    # Determine model type based on name
    model_type = ModelType.CHAT if (
        "chat" in model_name.lower() or 
        "qwen" in model_name.lower()  # Qwen models are chat models
    ) else ModelType.COMPLETION
    
    # Create default system prompt based on model type
    system_prompt = (
        "You are a helpful AI assistant. You provide clear, concise, and accurate responses."
        if model_type == ModelType.CHAT
        else None
    )
    
    # Set default capabilities based on model type
    capabilities = {
        ModelCapability.SYSTEM_PROMPT,
        ModelCapability.CHAT_HISTORY,
        ModelCapability.INSTRUCTION_FOLLOWING
    } if model_type == ModelType.CHAT else {
        ModelCapability.TEXT_COMPLETION
    }
    
    return ModelConfig(
        type=model_type,
        system_prompt=system_prompt,
        capabilities=capabilities,
        settings=get_default_settings(),
        notes=f"Configuration for {model_name}"
    )

def initialize_config_file() -> ModelConfigs:
    """Initialize the configuration file with default settings."""
    configs = ModelConfigs(
        defaults=get_default_settings(),
        models={}
    )
    save_configs(configs)
    return configs

def load_configs() -> ModelConfigs:
    """Load model configurations from YAML file."""
    ensure_config_dir()
    
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                data = yaml.safe_load(f)
                if data is not None:
                    try:
                        # Convert string values back to enums where needed
                        if 'models' in data:
                            for model_name, model_data in data['models'].items():
                                if 'type' in model_data:
                                    model_data['type'] = ModelType(model_data['type'])
                                if 'capabilities' in model_data:
                                    model_data['capabilities'] = {
                                        ModelCapability(cap) for cap in model_data['capabilities']
                                    }
                        return ModelConfigs(**data)
                    except Exception as e:
                        logger.error(f"Error parsing model configs: {str(e)}")
                        # If parsing fails, reinitialize the config file
                        return initialize_config_file()
        
        # Initialize new config file with defaults if it doesn't exist
        return initialize_config_file()
    except Exception as e:
        logger.error(f"Error loading model configs: {str(e)}")
        return initialize_config_file()

def save_configs(configs: ModelConfigs) -> bool:
    """Save model configurations to YAML file."""
    try:
        ensure_config_dir()
        # Convert to dict and ensure enums are serialized as strings
        config_dict = configs.model_dump(mode='json')  # This will convert enums to strings
        with open(CONFIG_FILE, 'w') as f:
            yaml.safe_dump(config_dict, f, default_flow_style=False)
        return True
    except Exception as e:
        logger.error(f"Error saving model configs: {str(e)}")
        return False

def get_model_config(model_name: str) -> Optional[ModelConfig]:
    """Get configuration for a specific model. Returns None if not configured."""
    configs = load_configs()
    return configs.models.get(model_name)

def create_or_update_model_config(model_name: str, config: Optional[ModelConfig] = None) -> ModelConfig:
    """Create or update configuration for a specific model."""
    configs = load_configs()
    
    if config is None:
        config = create_model_config(model_name)
    
    configs.models[model_name] = config
    if save_configs(configs):
        return config
    raise RuntimeError(f"Failed to save configuration for model {model_name}")

def update_model_config(model_name: str, config: ModelConfig) -> bool:
    """Update configuration for a specific model."""
    try:
        return create_or_update_model_config(model_name, config) is not None
    except Exception as e:
        logger.error(f"Error updating model config: {str(e)}")
        return False

def delete_model_config(model_name: str) -> bool:
    """Delete configuration for a specific model."""
    try:
        configs = load_configs()
        if model_name in configs.models:
            del configs.models[model_name]
            return save_configs(configs)
        return True  # Model config didn't exist, so deletion is successful
    except Exception as e:
        logger.error(f"Error deleting model config: {str(e)}")
        return False

def update_default_settings(settings: ModelSettings) -> bool:
    """Update default model settings."""
    try:
        configs = load_configs()
        configs.defaults = settings
        return save_configs(configs)
    except Exception as e:
        logger.error(f"Error updating default settings: {str(e)}")
        return False 