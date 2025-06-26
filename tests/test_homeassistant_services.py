"""
Tests for Home Assistant services with proper filtering handling.
"""

import pytest
import asyncio
from pathlib import Path
import logging
from orac.homeassistant.client import HomeAssistantClient
from orac.homeassistant.config import HomeAssistantConfig
from orac.homeassistant.cache import HomeAssistantCache

logger = logging.getLogger(__name__)

@pytest.fixture
async def ha_client():
    """Create a HomeAssistantClient instance for testing."""
    config_path = Path(__file__).parent.parent / "orac" / "homeassistant" / "config.yaml"
    config = HomeAssistantConfig.from_yaml(str(config_path))
    async with HomeAssistantClient(config) as client:
        yield client

@pytest.mark.asyncio
async def test_raw_services_vs_filtered(ha_client):
    """Test the difference between raw and filtered services."""
    print("\n=== Raw vs Filtered Services Test ===")
    
    # Get raw services directly from API (bypass cache and filtering)
    print("\nFetching raw services from Home Assistant API...")
    raw_services_data = await ha_client._request("GET", "/api/services")
    
    # Convert to dict if it's a list
    if isinstance(raw_services_data, list):
        raw_services = {entry['domain']: entry['services'] for entry in raw_services_data if 'domain' in entry and 'services' in entry}
    else:
        raw_services = raw_services_data
    
    print(f"Total raw service domains from Home Assistant: {len(raw_services)}")
    
    # Show all raw service domains
    print("\nAll raw service domains:")
    for domain in sorted(raw_services.keys()):
        service_count = len(raw_services[domain])
        print(f"- {domain}: {service_count} services")
    
    # Now get filtered services (with caching)
    print("\n=== Filtering Analysis ===")
    filtered_services = await ha_client.get_services()
    print(f"Filtered service domains (cached): {len(filtered_services)}")
    
    # Show what gets filtered
    cache = HomeAssistantCache()
    relevant_domains = []
    excluded_domains = []
    
    for domain in raw_services.keys():
        if cache._is_relevant_service(domain):
            relevant_domains.append(domain)
        else:
            excluded_domains.append(domain)
    
    print(f"Relevant domains (cached): {len(relevant_domains)}")
    print(f"Excluded domains: {len(excluded_domains)}")
    
    if relevant_domains:
        print(f"\nRelevant domains:")
        for domain in sorted(relevant_domains):
            print(f"  ✅ {domain}")
    
    if excluded_domains:
        print(f"\nExcluded domains:")
        for domain in sorted(excluded_domains):
            print(f"  ❌ {domain}")
    
    # Assertions with proper context
    assert len(raw_services) > 0, "No raw services found from Home Assistant"
    assert len(filtered_services) > 0, "No filtered services found"
    assert len(filtered_services) <= len(raw_services), "Filtered services should not exceed raw services"
    
    # Test that filtered services match our expectations
    expected_relevant_domains = cache.USER_CONTROLLABLE_SERVICES
    print(f"\nExpected relevant domains: {sorted(expected_relevant_domains)}")
    print(f"Actual relevant domains: {sorted(relevant_domains)}")
    
    # Check that all expected domains are present (if they exist in raw data)
    missing_expected = []
    for domain in expected_relevant_domains:
        if domain in raw_services and domain not in relevant_domains:
            missing_expected.append(domain)
    
    if missing_expected:
        print(f"⚠️  Expected domains missing from filtered results: {missing_expected}")
    else:
        print("✅ All expected domains are properly filtered")
    
    print(f"\n=== Test Summary ===")
    print(f"Raw service domains: {len(raw_services)}")
    print(f"Filtered service domains: {len(filtered_services)}")
    print(f"Filtering ratio: {len(filtered_services)/len(raw_services)*100:.1f}%")

@pytest.mark.asyncio
async def test_service_filtering_logic():
    """Test the service filtering logic independently."""
    print("\n=== Service Filtering Logic Test ===")
    
    cache = HomeAssistantCache()
    
    # Test domains that should be relevant
    relevant_test_domains = [
        'light', 'switch', 'climate', 'cover', 'media_player',
        'fan', 'lock', 'vacuum', 'scene', 'automation',
        'input_boolean', 'input_select', 'input_number', 'input_text', 'input_datetime',
        'homeassistant'
    ]
    
    # Test domains that should be excluded
    excluded_test_domains = [
        'sun', 'zone', 'conversation', 'weather', 'tts', 'todo', 'person',
        'recorder', 'cloud', 'frontend', 'backup', 'notify'
    ]
    
    print("\nTesting relevant domains:")
    for domain in relevant_test_domains:
        is_relevant = cache._is_relevant_service(domain)
        status = "✅" if is_relevant else "❌"
        print(f"  {status} {domain}: {is_relevant}")
        assert is_relevant, f"Domain '{domain}' should be relevant"
    
    print("\nTesting excluded domains:")
    for domain in excluded_test_domains:
        is_relevant = cache._is_relevant_service(domain)
        status = "✅" if not is_relevant else "❌"
        print(f"  {status} {domain}: {not is_relevant}")
        assert not is_relevant, f"Domain '{domain}' should be excluded"
    
    print("\n✅ Service filtering logic test passed")

@pytest.mark.asyncio
async def test_service_cache_consistency(ha_client):
    """Test that service cache is consistent between calls."""
    print("\n=== Service Cache Consistency Test ===")
    
    # Get services twice
    services1 = await ha_client.get_services()
    services2 = await ha_client.get_services()
    
    # Should be identical (using cache)
    assert len(services1) == len(services2), "Cached service counts should match"
    
    # Check that domains match
    domains1 = set(services1.keys())
    domains2 = set(services2.keys())
    assert domains1 == domains2, "Cached service domains should match"
    
    # Test cache bypass
    services_fresh = await ha_client.get_services(use_cache=False)
    assert len(services_fresh) == len(services1), "Fresh service counts should match cached"
    
    print(f"✅ Cache consistency test passed")
    print(f"   Cached services: {len(services1)} domains")
    print(f"   Fresh services: {len(services_fresh)} domains")

@pytest.mark.asyncio
async def test_service_data_structure(ha_client):
    """Test that service data has the expected structure."""
    print("\n=== Service Data Structure Test ===")
    
    services = await ha_client.get_services()
    
    for domain, domain_services in services.items():
        print(f"\nDomain: {domain}")
        print(f"  Services: {list(domain_services.keys())}")
        
        # Check that each service has expected structure
        for service_name, service_data in domain_services.items():
            assert isinstance(service_name, str), f"Service name should be string: {service_name}"
            assert isinstance(service_data, dict), f"Service data should be dict: {service_data}"
            
            # Check for common fields
            if 'name' in service_data:
                assert isinstance(service_data['name'], str), f"Service name field should be string"
            if 'description' in service_data:
                assert isinstance(service_data['description'], str), f"Service description should be string"
            if 'fields' in service_data:
                assert isinstance(service_data['fields'], dict), f"Service fields should be dict"
    
    print(f"✅ Service data structure test passed")
    print(f"   Tested {len(services)} domains")

if __name__ == "__main__":
    # Allow running this file directly for testing
    asyncio.run(test_raw_services_vs_filtered(ha_client())) 