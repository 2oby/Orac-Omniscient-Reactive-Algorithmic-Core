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

import time
from typing import Any, Dict, Optional
from loguru import logger

class HomeAssistantCache:
    """Cache manager for Home Assistant data."""
    
    def __init__(self, ttl: int = 300, max_size: int = 1000):
        """Initialize the cache with TTL and size limits.
        
        Args:
            ttl: Time-to-live for cache entries in seconds (default: 5 minutes)
            max_size: Maximum number of entries in cache (default: 1000)
        """
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._ttl = ttl
        self._max_size = max_size
        logger.debug(f"Initialized HomeAssistantCache with TTL={ttl}s, max_size={max_size}")
    
    def get(self, key: str) -> Optional[Any]:
        """Get a value from the cache if it exists and is not expired.
        
        Args:
            key: The cache key to retrieve
            
        Returns:
            The cached value if found and not expired, None otherwise
        """
        if key not in self._cache:
            return None
            
        entry = self._cache[key]
        if time.time() > entry['expires_at']:
            del self._cache[key]
            return None
            
        return entry['value']
    
    def set(self, key: str, value: Any) -> None:
        """Store a value in the cache with expiration.
        
        Args:
            key: The cache key
            value: The value to cache
        """
        # If cache is full, remove oldest entry
        if len(self._cache) >= self._max_size:
            oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k]['expires_at'])
            del self._cache[oldest_key]
            
        self._cache[key] = {
            'value': value,
            'expires_at': time.time() + self._ttl
        }
    
    def delete(self, key: str) -> None:
        """Remove a key from the cache.
        
        Args:
            key: The cache key to remove
        """
        self._cache.pop(key, None)
    
    def clear(self) -> None:
        """Clear all entries from the cache."""
        self._cache.clear()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.
        
        Returns:
            Dictionary containing cache statistics
        """
        return {
            'size': len(self._cache),
            'max_size': self._max_size,
            'ttl': self._ttl,
            'keys': list(self._cache.keys())
        } 