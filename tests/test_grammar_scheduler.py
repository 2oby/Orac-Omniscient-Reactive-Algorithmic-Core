#!/usr/bin/env python3
"""
Test script for the grammar scheduler functionality.

This script tests:
1. Grammar scheduler initialization
2. Manual grammar update with validation
3. Scheduler status checking
"""

import asyncio
import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from orac.homeassistant.config import HomeAssistantConfig
from orac.homeassistant.client import HomeAssistantClient
from orac.homeassistant.mapping_config import EntityMappingConfig
from orac.homeassistant.grammar_manager import HomeAssistantGrammarManager
from orac.homeassistant.grammar_scheduler import GrammarScheduler

async def test_grammar_scheduler():
    """Test the grammar scheduler functionality."""
    print("=== Testing Grammar Scheduler ===\n")
    
    try:
        # Initialize components
        print("1. Initializing components...")
        config_path = os.path.join(os.path.dirname(__file__), "orac", "homeassistant", "config.yaml")
        config = HomeAssistantConfig.from_yaml(config_path)
        
        async with HomeAssistantClient(config) as client:
            mapping_config = EntityMappingConfig(client=client)
            grammar_manager = HomeAssistantGrammarManager(client=client, mapping_config=mapping_config)
            scheduler = GrammarScheduler(grammar_manager, mapping_config, client)
            
            print("   ✅ Components initialized successfully")
            
            # Test scheduler status
            print("\n2. Testing scheduler status...")
            status = scheduler.get_status()
            print(f"   - Scheduler running: {status['scheduler_running']}")
            print(f"   - Last update: {status['last_update']}")
            print(f"   - Next update: {status['next_update']}")
            print(f"   - Update time: {status['update_time']}")
            
            # Test manual grammar update
            print("\n3. Testing manual grammar update...")
            result = await scheduler.update_grammar_with_validation(force_update=True)
            
            print(f"   - Status: {result['status']}")
            print(f"   - Message: {result['message']}")
            print(f"   - Elapsed time: {result['elapsed_seconds']:.2f} seconds")
            
            if result['status'] == 'success':
                validation = result['validation']
                print(f"   - Validation status: {validation['status']}")
                print(f"   - Validation message: {validation['message']}")
                if validation.get('parsed_json'):
                    print(f"   - Test response: {validation['parsed_json']}")
                
                grammar_stats = result['grammar_stats']
                print(f"   - Grammar stats: {grammar_stats}")
            
            # Test scheduler start/stop
            print("\n4. Testing scheduler start/stop...")
            await scheduler.start_scheduler()
            status = scheduler.get_status()
            print(f"   - Scheduler started: {status['scheduler_running']}")
            
            await scheduler.stop_scheduler()
            status = scheduler.get_status()
            print(f"   - Scheduler stopped: {status['scheduler_running']}")
            
            print("\n✅ All tests completed successfully!")
            
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = asyncio.run(test_grammar_scheduler())
    sys.exit(0 if success else 1) 