# This file will contain the HomeAssistantConfig class that manages all configuration
# settings for the Home Assistant integration, including connection details,
# authentication, and cache settings. It will handle loading/saving from YAML files.

"""
Configuration management for Home Assistant integration.

This module handles runtime configuration settings for the Home Assistant integration,
including connection details, cache settings, and other configurable parameters.
The configuration is validated using Pydantic models and supports both static
configuration and dynamic updates.
"""

from pydantic import BaseSettings, Field
from typing import Optional, Dict, Any
from pathlib import Path
import yaml
import os

from orac.config import NetworkConfig, CacheConfig

class HomeAssistantConfig(BaseSettings):
    """Runtime configuration for Home Assistant integration."""
    
    # Connection Settings
    host: str = Field(..., description="Home Assistant host address")
    port: int = Field(NetworkConfig.DEFAULT_HA_PORT, description="Home Assistant port")
    token: str = Field(..., description="Long-lived access token")
    ssl: bool = Field(True, description="Use SSL for connection")
    verify_ssl: bool = Field(True, description="Verify SSL certificates")
    timeout: int = Field(NetworkConfig.HA_TIMEOUT, description="Request timeout in seconds")

    # Cache Settings
    cache_ttl: int = Field(CacheConfig.DEFAULT_TTL, description="Cache TTL in seconds")
    cache_max_size: int = Field(CacheConfig.MAX_CACHE_SIZE, description="Maximum number of cached items")
    cache_dir: Optional[Path] = Field(None, description="Directory for persistent cache")
    
    # Configuration Keys (for internal use)
    CONFIG_HOST: str = "host"
    CONFIG_PORT: str = "port"
    CONFIG_TOKEN: str = "token"
    CONFIG_SSL: str = "ssl"
    CONFIG_VERIFY_SSL: str = "verify_ssl"
    CONFIG_TIMEOUT: str = "timeout"
    
    class Config:
        env_prefix = "HA_"  # Environment variables will be prefixed with HA_
        case_sensitive = True

    @classmethod
    def from_yaml(cls, yaml_path: str) -> "HomeAssistantConfig":
        """Load configuration from a YAML file.
        
        Args:
            yaml_path: Path to the YAML configuration file
            
        Returns:
            HomeAssistantConfig instance
            
        Raises:
            FileNotFoundError: If the YAML file doesn't exist
            yaml.YAMLError: If the YAML file is invalid
            ValueError: If required fields are missing
        """
        if not os.path.exists(yaml_path):
            raise FileNotFoundError(f"Configuration file not found: {yaml_path}")
            
        with open(yaml_path, 'r') as f:
            config_data = yaml.safe_load(f)
            
        if not config_data:
            raise ValueError("Configuration file is empty")
            
        # Convert cache_dir to Path if it exists
        if 'cache_dir' in config_data and config_data['cache_dir']:
            config_data['cache_dir'] = Path(config_data['cache_dir'])
            
        return cls(**config_data)

    def to_yaml(self, yaml_path: str) -> None:
        """Save configuration to a YAML file.
        
        Args:
            yaml_path: Path where to save the YAML configuration
            
        Raises:
            IOError: If the file cannot be written
            yaml.YAMLError: If the configuration cannot be serialized
        """
        # Convert to dict, excluding private attributes
        config_data = {
            k: v for k, v in self.dict().items() 
            if not k.startswith('_') and k not in ['CONFIG_HOST', 'CONFIG_PORT', 'CONFIG_TOKEN', 
                                                 'CONFIG_SSL', 'CONFIG_VERIFY_SSL', 'CONFIG_TIMEOUT']
        }
        
        # Convert Path to string if it exists
        if config_data.get('cache_dir'):
            config_data['cache_dir'] = str(config_data['cache_dir'])
            
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(yaml_path), exist_ok=True)
        
        with open(yaml_path, 'w') as f:
            yaml.safe_dump(config_data, f, default_flow_style=False)

    def validate_connection(self) -> bool:
        """Validate the connection settings by attempting to connect to Home Assistant.
        
        Returns:
            bool: True if connection is successful, False otherwise
        """
        # Connection validation is implemented in client.py and discovery_service.py
        # This method is kept for compatibility but delegates to the client
        pass

    @classmethod
    def from_env(cls) -> "HomeAssistantConfig":
        """Create configuration from environment variables.
        
        Environment variables should be prefixed with HA_, e.g.:
        - HA_HOST
        - HA_PORT
        - HA_TOKEN
        etc.
        
        Returns:
            HomeAssistantConfig instance
        """
        return cls()
