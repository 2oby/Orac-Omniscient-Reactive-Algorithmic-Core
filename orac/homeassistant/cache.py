"""
Caching system for Home Assistant integration.

This module provides caching functionality to optimize performance,
including:
- Entity state caching with TTL
- Service discovery caching
- Area/location caching
- Grammar and mapping caching
- Memory-efficient storage with size limits

The cache helps minimize API calls and disk reads while ensuring
data consistency through periodic updates.
"""

# This file will contain the HomeAssistantCache class that manages caching of
# Home Assistant data, including entities, services, and states. It will handle
# cache invalidation, TTL management, and persistence to disk. 