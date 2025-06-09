# This file will contain the HomeAssistantClient class that handles all direct communication
# with the Home Assistant API, including connection management, entity discovery,
# service calls, and state management.

"""
Home Assistant API client for ORAC.

This module provides a client for interacting with Home Assistant's REST API,
handling:
- Connection management and authentication
- Entity discovery and state management via /api/states
- Service discovery and execution via /api/services
- Area/location discovery via /api/areas
- Error handling and response processing
- Intelligent caching with filtering and persistence

The client is designed to support the command processing pipeline,
converting generic commands to specific Home Assistant API calls.
"""

import aiohttp
import asyncio
from typing import Dict, List, Optional, Any
from pathlib import Path
import logging
from .config import HomeAssistantConfig
from .constants import API_STATES, API_SERVICES, API_AREAS
from .models import HomeAssistantEntity, HomeAssistantService
from .cache import HomeAssistantCache

logger = logging.getLogger(__name__)

class HomeAssistantClient:
    """Client for interacting with Home Assistant's REST API."""
    
    def __init__(self, config: HomeAssistantConfig):
        """Initialize the Home Assistant client.
        
        Args:
            config: HomeAssistantConfig instance with connection details
        """
        self.config = config
        self._session: Optional[aiohttp.ClientSession] = None
        self._base_url = f"{'https' if config.ssl else 'http'}://{config.host}:{config.port}"
        self._headers = {
            "Authorization": f"Bearer {config.token}",
            "Content-Type": "application/json",
        }
        
        # Initialize cache with persistent storage if configured
        self._cache = HomeAssistantCache(
            ttl=config.cache_ttl,
            max_size=config.cache_max_size,
            cache_dir=config.cache_dir
        )

    async def __aenter__(self):
        """Create aiohttp session when entering async context."""
        if self._session is None:
            self._session = aiohttp.ClientSession(
                headers=self._headers,
                timeout=aiohttp.ClientTimeout(total=self.config.timeout)
            )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Close aiohttp session when exiting async context."""
        if self._session is not None:
            await self._session.close()
            self._session = None

    async def _request(self, method: str, endpoint: str, **kwargs) -> Any:
        """Make an HTTP request to the Home Assistant API.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint (e.g., /api/states)
            **kwargs: Additional arguments for aiohttp.ClientSession.request
            
        Returns:
            Response data
            
        Raises:
            aiohttp.ClientError: If the request fails
        """
        if self._session is None:
            raise RuntimeError("Client session not initialized. Use 'async with' context manager.")
            
        url = f"{self._base_url}{endpoint}"
        try:
            async with self._session.request(method, url, **kwargs) as response:
                response.raise_for_status()
                return await response.json()
        except aiohttp.ClientError as e:
            logger.error(f"API request failed: {e}")
            raise

    async def get_states(self, use_cache: bool = True) -> List[Dict[str, Any]]:
        """Get all entity states from Home Assistant.
        
        Args:
            use_cache: Whether to use cached data if available (default: True)
            
        Returns:
            List of entity states
        """
        # Try to get from cache first
        if use_cache:
            cached_entities = self._cache.get_entities()
            if cached_entities is not None:
                logger.debug("Using cached entities")
                return cached_entities
        
        # Fetch from API
        logger.debug("Fetching entities from Home Assistant API")
        entities = await self._request("GET", API_STATES)
        
        # Cache the entities with filtering
        self._cache.set_entities(entities)
        
        return entities

    async def get_services(self, use_cache: bool = True) -> Dict[str, Any]:
        """Get all available services from Home Assistant, normalized to a dict keyed by domain.
        
        Args:
            use_cache: Whether to use cached data if available (default: True)
            
        Returns:
            Dictionary of services
        """
        # Try to get from cache first
        if use_cache:
            cached_services = self._cache.get_services()
            if cached_services is not None:
                logger.debug("Using cached services")
                return cached_services
        
        # Fetch from API
        logger.debug("Fetching services from Home Assistant API")
        data = await self._request("GET", API_SERVICES)
        
        # If the response is a list, convert to dict
        if isinstance(data, list):
            services = {entry['domain']: entry['services'] for entry in data if 'domain' in entry and 'services' in entry}
        else:
            services = data
        
        # Cache the services with filtering
        self._cache.set_services(services)
        
        return services

    async def get_areas(self, use_cache: bool = True) -> List[Dict[str, Any]]:
        """Get all areas from Home Assistant.
        
        Args:
            use_cache: Whether to use cached data if available (default: True)
            
        Returns:
            List of areas
        """
        # Try to get from cache first
        if use_cache:
            cached_areas = self._cache.get_areas()
            if cached_areas is not None:
                logger.debug("Using cached areas")
                return cached_areas
        
        # Fetch from API
        logger.debug("Fetching areas from Home Assistant API")
        try:
            areas = await self._request("GET", API_AREAS)
            # Cache the areas
            self._cache.set_areas(areas)
            return areas
        except aiohttp.ClientError as e:
            logger.warning(f"Failed to fetch areas: {e}")
            # Return empty list if areas endpoint is not available
            return []

    async def validate_connection(self) -> bool:
        """Validate the connection to Home Assistant.
        
        Returns:
            bool: True if connection is successful
        """
        try:
            # Try to get states as a simple connection test
            await self.get_states(use_cache=False)
            return True
        except Exception as e:
            logger.error(f"Connection validation failed: {e}")
            return False

    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics.
        
        Returns:
            Dictionary containing cache statistics
        """
        return self._cache.get_stats()

    def cleanup_cache(self) -> None:
        """Clean up expired cache entries."""
        self._cache.cleanup_expired()

async def main():
    """Example usage of the Home Assistant client."""
    # Load configuration
    config_path = Path(__file__).parent / "config.yaml"
    config = HomeAssistantConfig.from_yaml(str(config_path))
    
    # Create and use client
    async with HomeAssistantClient(config) as client:
        # Validate connection
        if not await client.validate_connection():
            print("Failed to connect to Home Assistant")
            return
            
        # Get all data
        print("\nFetching Home Assistant data...")
        
        print("\nEntities:")
        entities = await client.get_states()
        print(f"Found {len(entities)} entities (filtered for relevance)")
        for entity in entities:
            print(f"- {entity['entity_id']}: {entity['state']}")
            
        print("\nServices:")
        services = await client.get_services()
        print(f"Found {len(services)} service domains (filtered for relevance)")
        for domain, domain_services in services.items():
            print(f"\n{domain}:")
            for service in domain_services:
                print(f"- {service}")
                
        print("\nAreas:")
        areas = await client.get_areas()
        print(f"Found {len(areas)} areas")
        for area in areas:
            print(f"- {area['name']} ({area['area_id']})")
        
        # Show cache statistics
        print("\nCache Statistics:")
        stats = client.get_cache_stats()
        for key, value in stats.items():
            print(f"- {key}: {value}")

if __name__ == "__main__":
    asyncio.run(main())
