#!/usr/bin/env python3
import asyncio
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'orac'))

from orac.homeassistant.client import HomeAssistantClient
from orac.homeassistant.config import HomeAssistantConfig

async def get_raw_entities():
    """Get raw entities data from Home Assistant without caching."""
    try:
        # Load configuration
        config_path = os.path.join(os.path.dirname(__file__), 'orac', 'homeassistant', 'config.yaml')
        config = HomeAssistantConfig.from_yaml(config_path)
        
        print(f"Connecting to Home Assistant at {config.host}:{config.port}")
        
        # Create and use client
        async with HomeAssistantClient(config) as client:
            # Get raw entities (bypass cache)
            print("Fetching raw entities from Home Assistant...")
            entities = await client.get_states(use_cache=False)
            
            print(f"\nTotal entities from Home Assistant: {len(entities)}")
            print("\nAll entities:")
            for entity in entities:
                print(f"- {entity['entity_id']}: {entity['state']}")
            
            # Show entity domains
            domains = {}
            for entity in entities:
                domain = entity['entity_id'].split('.')[0]
                domains[domain] = domains.get(domain, 0) + 1
            
            print(f"\nEntity domains:")
            for domain, count in sorted(domains.items()):
                print(f"- {domain}: {count} entities")
                
    except Exception as e:
        print(f"Error: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(get_raw_entities()) 