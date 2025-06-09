"""
Caching system for Home Assistant integration.

This module provides caching functionality to optimize performance,
including:
- Entity state caching with TTL
- Service discovery caching
- Area/location caching
- Grammar and mapping caching
- Memory-efficient storage with size limits
- Persistent disk storage for relevant objects

The cache helps minimize API calls and disk reads while ensuring
data consistency through periodic updates.
"""

import time
import json
import os
from typing import Any, Dict, Optional, List, Set
from pathlib import Path
from loguru import logger

class HomeAssistantCache:
    """Cache manager for Home Assistant data with persistent storage."""
    
    # Entity types that are most likely to be used in user commands
    USER_CONTROLLABLE_ENTITIES = {
        'light', 'switch', 'climate', 'cover', 'media_player', 
        'fan', 'lock', 'vacuum', 'scene'
    }
    
    # User-configurable virtual controls (input helpers)
    INPUT_HELPERS = {
        'input_boolean', 'input_select', 'input_number', 'input_text', 'input_datetime'
    }
    
    # Pre-configured automation entities (can be manually triggered)
    AUTOMATION_ENTITIES = {
        'automation'  # Only automations, not scripts
    }
    
    # Entity types for status queries (cache values, refresh more often)
    STATUS_ENTITIES = {
        'binary_sensor', 'sensor'
    }
    
    # Service domains that are most likely to be used in user commands
    USER_CONTROLLABLE_SERVICES = {
        'light', 'switch', 'climate', 'cover', 'media_player',
        'fan', 'lock', 'vacuum', 'scene', 'automation',  # Only automation, not script
        'input_boolean', 'input_select', 'input_number', 'input_text', 'input_datetime',
        'homeassistant'  # Generic services
    }
    
    # System entities that should NOT be cached (rarely used in user commands)
    SYSTEM_ENTITIES = {
        'sun', 'zone', 'conversation', 'weather', 'tts', 'todo', 'person'
    }
    
    def __init__(self, ttl: int = 300, max_size: int = 1000, cache_dir: Optional[Path] = None):
        """Initialize the cache with TTL and size limits.
        
        Args:
            ttl: Time-to-live for cache entries in seconds (default: 5 minutes)
            max_size: Maximum number of entries in cache (default: 1000)
            cache_dir: Directory for persistent cache storage (optional)
        """
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._ttl = ttl
        self._max_size = max_size
        self._cache_dir = cache_dir
        
        # Create cache directory if specified
        if self._cache_dir:
            self._cache_dir.mkdir(parents=True, exist_ok=True)
            logger.info(f"Persistent cache directory: {self._cache_dir}")
        
        logger.debug(f"Initialized HomeAssistantCache with TTL={ttl}s, max_size={max_size}")
    
    def _is_relevant_entity(self, entity_id: str) -> bool:
        """Check if an entity is relevant for user commands.
        
        Args:
            entity_id: The entity ID to check
            
        Returns:
            bool: True if the entity is relevant for caching
        """
        domain = entity_id.split('.')[0] if '.' in entity_id else ''
        
        # Don't cache system entities
        if domain in self.SYSTEM_ENTITIES:
            return False
        
        # Cache user-controllable entities, input helpers, automation entities, and status entities
        return (domain in self.USER_CONTROLLABLE_ENTITIES or 
                domain in self.INPUT_HELPERS or 
                domain in self.AUTOMATION_ENTITIES or 
                domain in self.STATUS_ENTITIES)
    
    def _is_relevant_service(self, domain: str) -> bool:
        """Check if a service domain is relevant for user commands.
        
        Args:
            domain: The service domain to check
            
        Returns:
            bool: True if the service domain is relevant for caching
        """
        return domain in self.USER_CONTROLLABLE_SERVICES
    
    def _get_cache_file_path(self, key: str) -> Optional[Path]:
        """Get the file path for a cache key.
        
        Args:
            key: The cache key
            
        Returns:
            Optional[Path]: The file path for the cache entry
        """
        if not self._cache_dir:
            return None
        
        # Sanitize key for filename
        safe_key = "".join(c for c in key if c.isalnum() or c in ('-', '_')).rstrip()
        return self._cache_dir / f"{safe_key}.json"
    
    def get(self, key: str) -> Optional[Any]:
        """Get a value from the cache if it exists and is not expired.
        
        Args:
            key: The cache key to retrieve
            
        Returns:
            The cached value if found and not expired, None otherwise
        """
        # Check memory cache first
        if key in self._cache:
            entry = self._cache[key]
            if time.time() > entry['expires_at']:
                del self._cache[key]
            else:
                return entry['value']
        
        # Check persistent cache if available
        if self._cache_dir:
            cache_file = self._get_cache_file_path(key)
            if cache_file and cache_file.exists():
                try:
                    with open(cache_file, 'r') as f:
                        entry = json.load(f)
                    
                    # Check if expired
                    if time.time() > entry['expires_at']:
                        cache_file.unlink()  # Remove expired file
                        return None
                    
                    # Load into memory cache
                    self._cache[key] = entry
                    return entry['value']
                    
                except (json.JSONDecodeError, IOError) as e:
                    logger.warning(f"Error reading cache file {cache_file}: {e}")
                    # Remove corrupted file
                    if cache_file.exists():
                        cache_file.unlink()
        
        return None
    
    def set(self, key: str, value: Any, persist: bool = True) -> None:
        """Store a value in the cache with expiration.
        
        Args:
            key: The cache key
            value: The value to cache
            persist: Whether to persist to disk (default: True)
        """
        # If cache is full, remove oldest entry
        if len(self._cache) >= self._max_size:
            oldest_key = min(self._cache.keys(), key=lambda k: self._cache[k]['expires_at'])
            del self._cache[oldest_key]
        
        entry = {
            'value': value,
            'expires_at': time.time() + self._ttl,
            'created_at': time.time()
        }
        
        # Store in memory cache
        self._cache[key] = entry
        
        # Store in persistent cache if requested and directory is available
        if persist and self._cache_dir:
            cache_file = self._get_cache_file_path(key)
            if cache_file:
                try:
                    with open(cache_file, 'w') as f:
                        json.dump(entry, f, indent=2)
                except IOError as e:
                    logger.warning(f"Error writing cache file {cache_file}: {e}")
    
    def set_entities(self, entities: List[Dict[str, Any]]) -> None:
        """Cache relevant entities with filtering.
        
        Args:
            entities: List of entity dictionaries from Home Assistant
        """
        relevant_entities = []
        system_entities = []
        
        for entity in entities:
            entity_id = entity.get('entity_id', '')
            if self._is_relevant_entity(entity_id):
                relevant_entities.append(entity)
            else:
                domain = entity_id.split('.')[0] if '.' in entity_id else ''
                if domain in self.SYSTEM_ENTITIES:
                    system_entities.append(entity_id)
        
        logger.info(f"Caching {len(relevant_entities)} relevant entities out of {len(entities)} total")
        if system_entities:
            logger.debug(f"Excluded {len(system_entities)} system entities: {system_entities[:5]}{'...' if len(system_entities) > 5 else ''}")
        
        self.set('entities', relevant_entities, persist=True)
    
    def set_services(self, services: Dict[str, Any]) -> None:
        """Cache relevant services with filtering.
        
        Args:
            services: Dictionary of services from Home Assistant
        """
        relevant_services = {}
        excluded_services = []
        
        for domain, domain_services in services.items():
            if self._is_relevant_service(domain):
                relevant_services[domain] = domain_services
            else:
                excluded_services.append(domain)
        
        logger.info(f"Caching {len(relevant_services)} relevant service domains out of {len(services)} total")
        if excluded_services:
            logger.debug(f"Excluded {len(excluded_services)} non-relevant service domains: {excluded_services[:5]}{'...' if len(excluded_services) > 5 else ''}")
        
        self.set('services', relevant_services, persist=True)
    
    def set_areas(self, areas: List[Dict[str, Any]]) -> None:
        """Cache areas (always relevant for location-based commands).
        
        Args:
            areas: List of area dictionaries from Home Assistant
        """
        logger.info(f"Caching {len(areas)} areas")
        self.set('areas', areas, persist=True)
    
    def get_entities(self) -> Optional[List[Dict[str, Any]]]:
        """Get cached entities.
        
        Returns:
            List of entity dictionaries or None if not cached
        """
        return self.get('entities')
    
    def get_services(self) -> Optional[Dict[str, Any]]:
        """Get cached services.
        
        Returns:
            Dictionary of services or None if not cached
        """
        return self.get('services')
    
    def get_areas(self) -> Optional[List[Dict[str, Any]]]:
        """Get cached areas.
        
        Returns:
            List of area dictionaries or None if not cached
        """
        return self.get('areas')
    
    def delete(self, key: str) -> None:
        """Remove a key from the cache.
        
        Args:
            key: The cache key to remove
        """
        self._cache.pop(key, None)
        
        # Remove from persistent cache if available
        if self._cache_dir:
            cache_file = self._get_cache_file_path(key)
            if cache_file and cache_file.exists():
                cache_file.unlink()
    
    def clear(self) -> None:
        """Clear all entries from the cache."""
        self._cache.clear()
        
        # Clear persistent cache if available
        if self._cache_dir and self._cache_dir.exists():
            for cache_file in self._cache_dir.glob("*.json"):
                cache_file.unlink()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.
        
        Returns:
            Dictionary containing cache statistics
        """
        stats = {
            'memory_size': len(self._cache),
            'max_size': self._max_size,
            'ttl': self._ttl,
            'memory_keys': list(self._cache.keys())
        }
        
        if self._cache_dir and self._cache_dir.exists():
            persistent_files = list(self._cache_dir.glob("*.json"))
            stats['persistent_files'] = len(persistent_files)
            stats['persistent_keys'] = [f.stem for f in persistent_files]
        
        return stats
    
    def cleanup_expired(self) -> None:
        """Clean up expired entries from both memory and persistent cache."""
        # Clean memory cache
        expired_keys = [
            key for key, entry in self._cache.items() 
            if time.time() > entry['expires_at']
        ]
        for key in expired_keys:
            del self._cache[key]
        
        # Clean persistent cache
        if self._cache_dir and self._cache_dir.exists():
            for cache_file in self._cache_dir.glob("*.json"):
                try:
                    with open(cache_file, 'r') as f:
                        entry = json.load(f)
                    
                    if time.time() > entry['expires_at']:
                        cache_file.unlink()
                        logger.debug(f"Removed expired cache file: {cache_file}")
                        
                except (json.JSONDecodeError, IOError):
                    # Remove corrupted files
                    cache_file.unlink()
                    logger.warning(f"Removed corrupted cache file: {cache_file}")
        
        if expired_keys:
            logger.info(f"Cleaned up {len(expired_keys)} expired cache entries") 