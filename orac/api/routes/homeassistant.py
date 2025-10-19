"""
orac.api.routes.homeassistant
------------------------------
Home Assistant specific endpoints for cache management.
"""

import os
from fastapi import APIRouter, HTTPException
from typing import Dict, Any

from orac.logger import get_logger
from orac.homeassistant.client import HomeAssistantClient
from orac.homeassistant.config import HomeAssistantConfig
from orac.api.dependencies import get_ha_client

logger = get_logger(__name__)

router = APIRouter(tags=["Home Assistant"])


@router.post("/v1/homeassistant/cache")
async def create_homeassistant_cache() -> Dict[str, Any]:
    """Create Home Assistant cache by fetching entities, services, and areas."""
    try:
        # Load configuration
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "homeassistant", "config.yaml")
        config = HomeAssistantConfig.from_yaml(config_path)

        logger.info(f"Creating Home Assistant cache for {config.host}:{config.port}")

        # Create client and fetch data to trigger cache
        async with HomeAssistantClient(config) as client:
            # Fetch entities
            logger.info("Fetching entities...")
            entities = await client.get_states(use_cache=False)  # Force fresh fetch

            # Fetch services
            logger.info("Fetching services...")
            services = await client.get_services(use_cache=False)  # Force fresh fetch

            # Fetch areas
            logger.info("Fetching areas...")
            areas = await client.get_areas(use_cache=False)  # Force fresh fetch

            # Get cache stats
            cache_stats = client.get_cache_stats()

            return {
                "status": "success",
                "message": "Home Assistant cache created successfully",
                "cache_stats": cache_stats,
                "entities_fetched": len(entities),
                "service_domains_fetched": len(services),
                "areas_fetched": len(areas),
                "cache_directory": str(config.cache_dir) if config.cache_dir else None
            }

    except Exception as e:
        logger.error(f"Error creating Home Assistant cache: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/v1/homeassistant/cache/stats")
async def get_homeassistant_cache_stats() -> Dict[str, Any]:
    """Get Home Assistant cache statistics."""
    try:
        client = await get_ha_client()
        cache = client.cache

        # Get cache statistics
        stats = cache.get_stats()

        return {
            "status": "success",
            "cache_stats": stats,
            "cache_enabled": cache.is_enabled(),
            "cache_directory": cache.cache_dir if hasattr(cache, 'cache_dir') else None
        }
    except Exception as e:
        logger.error(f"Error getting Home Assistant cache stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
