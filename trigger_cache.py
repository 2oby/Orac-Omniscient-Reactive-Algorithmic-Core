#!/usr/bin/env python3
"""
Script to trigger Home Assistant cache creation.
This will make API calls to fetch entities, services, and areas,
which will populate the cache directory.
"""

import asyncio
import os
import sys
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from orac.homeassistant.client import HomeAssistantClient
from orac.homeassistant.config import HomeAssistantConfig

async def trigger_cache_creation():
    """Trigger cache creation by fetching Home Assistant data."""
    try:
        # Load configuration
        config_path = os.path.join(os.path.dirname(__file__), 'orac', 'homeassistant', 'config.yaml')
        config = HomeAssistantConfig.from_yaml(config_path)
        
        print(f"Connecting to Home Assistant at {config.host}:{config.port}")
        print(f"Cache directory: {config.cache_dir}")
        
        # Create client and fetch data to trigger cache
        async with HomeAssistantClient(config) as client:
            print("Fetching entities...")
            entities = await client.get_states(use_cache=False)  # Force fresh fetch
            print(f"Fetched {len(entities)} entities")
            
            print("Fetching services...")
            services = await client.get_services(use_cache=False)  # Force fresh fetch
            print(f"Fetched {len(services)} service domains")
            
            print("Fetching areas...")
            areas = await client.get_areas(use_cache=False)  # Force fresh fetch
            print(f"Fetched {len(areas)} areas")
            
            # Get cache stats
            cache_stats = client.get_cache_stats()
            print(f"Cache stats: {cache_stats}")
            
            print("Cache creation completed successfully!")
            
    except Exception as e:
        print(f"Error creating cache: {e}")
        return False
    
    return True

if __name__ == "__main__":
    success = asyncio.run(trigger_cache_creation())
    sys.exit(0 if success else 1) 