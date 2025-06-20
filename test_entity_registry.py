#!/usr/bin/env python3
"""
Test script to verify Entity Registry API endpoints.
"""

import asyncio
import logging
from pathlib import Path
from orac.homeassistant.client import HomeAssistantClient
from orac.homeassistant.config import HomeAssistantConfig

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_entity_registry():
    """Test the Entity Registry API endpoints."""
    try:
        # Load configuration
        config_path = Path("orac/homeassistant/config.yaml")
        config = HomeAssistantConfig.from_yaml(str(config_path))
        
        logger.info(f"Testing Entity Registry endpoints for Home Assistant at {config.host}:{config.port}")
        
        # Create and use client
        async with HomeAssistantClient(config) as client:
            # Test Entity Registry
            logger.info("Testing Entity Registry...")
            entity_registry = await client.get_entity_registry()
            logger.info(f"✅ Found {len(entity_registry)} entity registry entries")
            
            if entity_registry:
                logger.info("Sample entity registry entries:")
                for entry in entity_registry[:3]:  # Show first 3 entries
                    logger.info(f"  - {entry.get('entity_id', 'Unknown')}: {entry.get('name', 'No name')}")
            
            # Test Device Registry
            logger.info("Testing Device Registry...")
            device_registry = await client.get_device_registry()
            logger.info(f"✅ Found {len(device_registry)} device registry entries")
            
            if device_registry:
                logger.info("Sample device registry entries:")
                for device in device_registry[:3]:  # Show first 3 entries
                    logger.info(f"  - {device.get('name', 'Unknown')} ({device.get('device_id', 'No ID')})")
            
            logger.info("✅ Entity Registry API endpoints test completed successfully!")
                
    except Exception as e:
        logger.error(f"❌ Error during Entity Registry test: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(test_entity_registry()) 