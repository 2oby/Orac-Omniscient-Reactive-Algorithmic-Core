#!/usr/bin/env python3
"""
Test script to demonstrate the enhanced Home Assistant caching functionality.
This script shows how the cache filters relevant objects and persists them to disk.
"""

import asyncio
import logging
from pathlib import Path
from .client import HomeAssistantClient
from .config import HomeAssistantConfig

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_enhanced_caching():
    """Test the enhanced caching functionality."""
    try:
        # Load configuration
        config_path = Path(__file__).parent / "config.yaml"
        config = HomeAssistantConfig.from_yaml(str(config_path))
        
        logger.info(f"Testing enhanced caching with Home Assistant at {config.host}:{config.port}")
        logger.info("=" * 60)
        
        # Create client with enhanced cache
        async with HomeAssistantClient(config) as client:
            # Fetch and cache data
            logger.info("📡 Fetching Home Assistant data...")
            entities = await client.get_entities()
            services = await client.get_services()
            areas = await client.get_areas()
            
            # Get cache statistics
            cache_stats = client.cache.get_stats()
            
            logger.info("📊 Cache Statistics:")
            logger.info(f"   Memory entries: {cache_stats['memory_size']}")
            logger.info(f"   Persistent files: {cache_stats.get('persistent_files', 0)}")
            logger.info(f"   TTL: {cache_stats['ttl']} seconds")
            
            # Analyze cached entities by category
            cached_entities = client.cache.get_entities() or []
            
            categories = {
                'User Controllable': [],
                'Input Helpers': [],
                'Automations': [],
                'Status Entities': [],
                'System Entities': []
            }
            
            for entity in cached_entities:
                entity_id = entity.get('entity_id', '')
                domain = entity_id.split('.')[0] if '.' in entity_id else ''
                
                if domain in client.cache.USER_CONTROLLABLE_ENTITIES:
                    categories['User Controllable'].append(entity_id)
                elif domain in client.cache.INPUT_HELPERS:
                    categories['Input Helpers'].append(entity_id)
                elif domain in client.cache.AUTOMATION_ENTITIES:
                    categories['Automations'].append(entity_id)
                elif domain in client.cache.STATUS_ENTITIES:
                    categories['Status Entities'].append(entity_id)
                else:
                    categories['System Entities'].append(entity_id)
            
            logger.info("\n🏠 Cached Entity Categories:")
            for category, entity_list in categories.items():
                if entity_list:
                    logger.info(f"   {category} ({len(entity_list)}):")
                    for entity_id in entity_list[:3]:  # Show first 3
                        logger.info(f"     • {entity_id}")
                    if len(entity_list) > 3:
                        logger.info(f"     ... and {len(entity_list) - 3} more")
                else:
                    logger.info(f"   {category}: None found")
            
            # Show cached services
            cached_services = client.cache.get_services() or {}
            logger.info(f"\n🔧 Cached Service Domains ({len(cached_services)}):")
            for domain in sorted(cached_services.keys()):
                logger.info(f"   • {domain}")
            
            # Show cached areas
            cached_areas = client.cache.get_areas() or []
            logger.info(f"\n📍 Cached Areas ({len(cached_areas)}):")
            for area in cached_areas:
                area_name = area.get('name', 'Unknown')
                area_id = area.get('area_id', 'unknown')
                logger.info(f"   • {area_name} ({area_id})")
            
            # Test cache persistence
            logger.info("\n💾 Testing Cache Persistence:")
            if cache_stats.get('persistent_files', 0) > 0:
                logger.info("   ✅ Persistent cache files created successfully")
                logger.info(f"   📁 Cache directory: {client.cache._cache_dir}")
            else:
                logger.info("   ⚠️  No persistent cache files created (check cache_dir config)")
            
            # Show example commands that would use cached data
            logger.info("\n🎯 Example User Commands Using Cached Data:")
            
            # User controllable examples
            if categories['User Controllable']:
                example_entity = categories['User Controllable'][0]
                logger.info(f"   • \"Turn on {example_entity}\"")
                logger.info(f"   • \"Set {example_entity} to 50%\"" if 'light' in example_entity else f"   • \"Toggle {example_entity}\"")
            
            # Input helper examples
            if categories['Input Helpers']:
                example_input = categories['Input Helpers'][0]
                if 'input_boolean' in example_input:
                    logger.info(f"   • \"Enable {example_input}\"")
                elif 'input_select' in example_input:
                    logger.info(f"   • \"Set {example_input} to Normal\"")
                elif 'input_number' in example_input:
                    logger.info(f"   • \"Set {example_input} to 22\"")
            
            # Automation examples
            if categories['Automations']:
                example_automation = categories['Automations'][0]
                logger.info(f"   • \"Run {example_automation}\"")
                logger.info(f"   • \"Trigger {example_automation}\"")
            
            # Area-based examples
            if cached_areas:
                example_area = cached_areas[0].get('name', 'Living Room')
                logger.info(f"   • \"Turn on all lights in {example_area}\"")
                logger.info(f"   • \"What's the temperature in {example_area}?\"" if categories['Status Entities'] else f"   • \"Show me {example_area}\"")
            
            logger.info("\n✅ Enhanced caching test completed successfully!")
            
    except Exception as e:
        logger.error(f"❌ Error during enhanced caching test: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(test_enhanced_caching()) 