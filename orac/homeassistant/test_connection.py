#!/usr/bin/env python3
"""
Test script to verify connection to Home Assistant.
This script will attempt to connect to Home Assistant and fetch basic information.
"""

import asyncio
import logging
from pathlib import Path
from .client import HomeAssistantClient
from .config import HomeAssistantConfig

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_connection():
    """Test the connection to Home Assistant."""
    try:
        # Load configuration
        config_path = Path(__file__).parent / "config.yaml"
        config = HomeAssistantConfig.from_yaml(str(config_path))
        
        logger.info(f"Attempting to connect to Home Assistant at {config.host}:{config.port}")
        
        # Create and use client
        async with HomeAssistantClient(config) as client:
            # Validate connection
            if await client.validate_connection():
                logger.info("✅ Successfully connected to Home Assistant!")
                
                # Get some basic information
                logger.info("\nFetching basic information...")
                
                # Get entities count
                entities = await client.get_states()
                logger.info(f"Found {len(entities)} entities")
                
                # Get services count
                services = await client.get_services()
                service_count = sum(len(domain_services) for domain_services in services.values())
                logger.info(f"Found {service_count} services across {len(services)} domains")
                
                # Get areas count
                areas = await client.get_areas()
                logger.info(f"Found {len(areas)} areas")
                
            else:
                logger.error("❌ Failed to connect to Home Assistant")
                
    except Exception as e:
        logger.error(f"❌ Error during connection test: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(test_connection()) 