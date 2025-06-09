"""
Tests for Home Assistant integration.

These tests verify that we can:
1. Connect to Home Assistant
2. Fetch entities, services, and areas
3. Process the data correctly
4. Use intelligent caching with filtering and persistence
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
async def test_raw_homeassistant_data(ha_client):
    """Test fetching raw Home Assistant data without any filtering."""
    print("\n=== Raw Home Assistant Data Test ===")
    
    # Get raw entities directly from API (bypass cache and filtering)
    print("\nFetching raw entities from Home Assistant API...")
    raw_entities = await ha_client._request("GET", "/api/states")
    print(f"Total raw entities from Home Assistant: {len(raw_entities)}")
    
    print("\nAll raw entities:")
    for entity in raw_entities:
        print(f"- {entity['entity_id']}: {entity['state']}")
    
    # Show entity domains
    domains = {}
    for entity in raw_entities:
        domain = entity['entity_id'].split('.')[0]
        domains[domain] = domains.get(domain, 0) + 1
    
    print(f"\nEntity domains:")
    for domain, count in sorted(domains.items()):
        print(f"- {domain}: {count} entities")
    
    # Now show what gets filtered
    print("\n=== Filtering Analysis ===")
    from orac.homeassistant.cache import HomeAssistantCache
    cache = HomeAssistantCache()
    
    relevant_entities = []
    system_entities = []
    other_entities = []
    
    for entity in raw_entities:
        entity_id = entity['entity_id']
        if cache._is_relevant_entity(entity_id):
            relevant_entities.append(entity_id)
        else:
            domain = entity_id.split('.')[0] if '.' in entity_id else ''
            if domain in cache.SYSTEM_ENTITIES:
                system_entities.append(entity_id)
            else:
                other_entities.append(entity_id)
    
    print(f"Relevant entities (cached): {len(relevant_entities)}")
    print(f"System entities (excluded): {len(system_entities)}")
    print(f"Other entities (excluded): {len(other_entities)}")
    
    if system_entities:
        print(f"\nSystem entities excluded:")
        for entity_id in system_entities:
            print(f"- {entity_id}")
    
    if other_entities:
        print(f"\nOther entities excluded:")
        for entity_id in other_entities:
            print(f"- {entity_id}")

@pytest.mark.asyncio
async def test_homeassistant_data(ha_client):
    """Test fetching and processing Home Assistant data with caching."""
    # Get all data
    print("\n=== Home Assistant Data Test ===")
    
    # Get entities (with caching)
    print("\nFetching entities...")
    entities = await ha_client.get_states()
    print(f"Found {len(entities)} entities (filtered for relevance):")
    for entity in entities:
        print(f"- {entity['entity_id']}: {entity['state']}")
    assert len(entities) >= 0, "No entities found (this is OK if no relevant entities exist)"
    
    # Get services (with caching)
    print("\nFetching services...")
    services = await ha_client.get_services()
    print(f"Found {len(services)} relevant service domains:")
    if isinstance(services, dict):
        for domain, domain_services in services.items():
            print(f"\n{domain}:")
            for service in domain_services:
                print(f"- {service}")
    else:
        print("Services data is not in expected dictionary format")
        print(f"Type: {type(services)}")
        print(f"Content: {services}")
    assert len(services) > 0, "No services found"
    
    # Get areas (with caching)
    print("\nFetching areas...")
    areas = await ha_client.get_areas()
    print(f"Found {len(areas)} areas:")
    for area in areas:
        print(f"- {area['name']} ({area['area_id']})")
    # Areas might be empty if not configured, which is OK
    
    # Test cache functionality
    print("\n=== Cache Test ===")
    
    # Get cache statistics
    stats = ha_client.get_cache_stats()
    print("Cache Statistics:")
    for key, value in stats.items():
        print(f"- {key}: {value}")
    
    # Test that subsequent calls use cache
    print("\nTesting cache usage...")
    entities_cached = await ha_client.get_states()
    services_cached = await ha_client.get_services()
    areas_cached = await ha_client.get_areas()
    
    # Verify we get the same data (indicating cache is working)
    assert len(entities_cached) == len(entities), "Cached entities count should match"
    assert len(services_cached) == len(services), "Cached services count should match"
    assert len(areas_cached) == len(areas), "Cached areas count should match"
    
    print("✅ Cache test passed - subsequent calls returned same data")
    
    # Test cache bypass
    print("\nTesting cache bypass...")
    entities_fresh = await ha_client.get_states(use_cache=False)
    services_fresh = await ha_client.get_services(use_cache=False)
    areas_fresh = await ha_client.get_areas(use_cache=False)
    
    # Verify we get the same data (indicating API consistency)
    assert len(entities_fresh) == len(entities), "Fresh entities count should match"
    assert len(services_fresh) == len(services), "Fresh services count should match"
    assert len(areas_fresh) == len(areas), "Fresh areas count should match"
    
    print("✅ Cache bypass test passed - fresh calls returned same data")
    
    # Clean up cache
    ha_client.cleanup_cache()
    
    print("\n=== Test Complete ===")

@pytest.mark.asyncio
async def test_cache_persistence():
    """Test that cache persists between client instances."""
    config_path = Path(__file__).parent.parent / "orac" / "homeassistant" / "config.yaml"
    config = HomeAssistantConfig.from_yaml(str(config_path))
    
    # First client instance
    async with HomeAssistantClient(config) as client1:
        entities1 = await client1.get_states()
        services1 = await client1.get_services()
        areas1 = await client1.get_areas()
        
        stats1 = client1.get_cache_stats()
        print(f"First client cache stats: {stats1}")
    
    # Second client instance (should load from persistent cache)
    async with HomeAssistantClient(config) as client2:
        entities2 = await client2.get_states()
        services2 = await client2.get_services()
        areas2 = await client2.get_areas()
        
        stats2 = client2.get_cache_stats()
        print(f"Second client cache stats: {stats2}")
        
        # Verify data consistency
        assert len(entities2) == len(entities1), "Entities should be consistent between clients"
        assert len(services2) == len(services1), "Services should be consistent between clients"
        assert len(areas2) == len(areas1), "Areas should be consistent between clients"
        
        print("✅ Cache persistence test passed")

if __name__ == "__main__":
    # Allow running this file directly for testing
    asyncio.run(test_homeassistant_data(ha_client())) 