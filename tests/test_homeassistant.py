"""
Tests for Home Assistant integration.

These tests verify that we can:
1. Connect to Home Assistant
2. Fetch entities, services, and areas
3. Process the data correctly
"""

import pytest
import asyncio
from pathlib import Path
import logging
from orac.homeassistant.client import HomeAssistantClient
from orac.homeassistant.config import HomeAssistantConfig

logger = logging.getLogger(__name__)

@pytest.fixture
async def ha_client():
    """Create a HomeAssistantClient instance for testing."""
    config_path = Path(__file__).parent.parent / "orac" / "homeassistant" / "config.yaml"
    config = HomeAssistantConfig.from_yaml(str(config_path))
    async with HomeAssistantClient(config) as client:
        yield client

@pytest.mark.asyncio
async def test_homeassistant_connection(ha_client):
    """Test connection to Home Assistant."""
    # Validate connection
    assert await ha_client.validate_connection(), "Failed to connect to Home Assistant"

@pytest.mark.asyncio
async def test_homeassistant_data(ha_client):
    """Test fetching and processing Home Assistant data."""
    # Get all data
    print("\n=== Home Assistant Data Test ===")
    
    # Get entities
    print("\nFetching entities...")
    entities = await ha_client.get_states()
    print(f"Found {len(entities)} entities:")
    for entity in entities:
        print(f"- {entity['entity_id']}: {entity['state']}")
    assert len(entities) > 0, "No entities found"
    
    # Get services
    print("\nFetching services...")
    services = await ha_client.get_services()
    print(f"Found {len(services)} service domains:")
    for domain, domain_services in services.items():
        print(f"\n{domain}:")
        for service in domain_services:
            print(f"- {service}")
    assert len(services) > 0, "No services found"
    
    # Get areas
    print("\nFetching areas...")
    areas = await ha_client.get_areas()
    print(f"Found {len(areas)} areas:")
    for area in areas:
        print(f"- {area['name']} ({area['area_id']})")
    assert len(areas) > 0, "No areas found"
    
    print("\n=== Test Complete ===")

if __name__ == "__main__":
    # Allow running this file directly for testing
    asyncio.run(test_homeassistant_data(ha_client())) 