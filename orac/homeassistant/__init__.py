"""
orac.homeassistant
-----------------
Home Assistant integration module for ORAC.

This module provides:
- Connection to Home Assistant instance
- Entity and service discovery
- Grammar generation for Home Assistant commands
- Caching of Home Assistant data
"""

from .client import HomeAssistantClient
from .models import HomeAssistantEntity, HomeAssistantService
from .config import HomeAssistantConfig
from .cache import HomeAssistantCache

__version__ = "0.1.0"

__all__ = [
    'HomeAssistantClient',
    'HomeAssistantEntity',
    'HomeAssistantService',
    'HomeAssistantConfig',
    'HomeAssistantCache'
] 