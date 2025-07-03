#!/usr/bin/env python3
"""
Test script for model settings persistence.

This script tests:
1. Saving model settings
2. Loading model settings
3. Verifying settings are not lost
"""

import asyncio
import sys
import os
import json
import requests

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from orac.config import load_favorites, load_model_configs, save_favorites, save_model_configs

def test_settings_persistence():
    """Test that model settings are properly saved and loaded."""
    print("=== Testing Model Settings Persistence ===\n")
    
    # Test 1: Load current settings
    print("1. Loading current settings...")
    try:
        favorites = load_favorites()
        model_configs = load_model_configs()
        print(f"   ✅ Favorites loaded: {len(favorites.get('favorite_models', []))} models")
        print(f"   ✅ Model configs loaded: {len(model_configs.get('models', {}))} models")
    except Exception as e:
        print(f"   ❌ Failed to load settings: {e}")
        return False
    
    # Test 2: Check if default model has settings
    default_model = favorites.get('default_model')
    if default_model:
        print(f"\n2. Checking settings for default model: {default_model}")
        model_config = model_configs.get('models', {}).get(default_model, {})
        settings = model_config.get('recommended_settings', {})
        
        required_fields = ['temperature', 'top_p', 'top_k', 'max_tokens']
        missing_fields = [field for field in required_fields if field not in settings]
        
        if missing_fields:
            print(f"   ⚠️  Missing settings: {missing_fields}")
            print(f"   Current settings: {settings}")
        else:
            print(f"   ✅ All required settings present: {settings}")
    else:
        print("\n2. No default model set")
    
    # Test 3: Test saving new settings
    print("\n3. Testing settings save/load...")
    test_model = "test-model-settings.gguf"
    test_settings = {
        "temperature": 0.5,
        "top_p": 0.8,
        "top_k": 30,
        "max_tokens": 100,
        "json_mode": True
    }
    
    try:
        # Save test settings
        new_config = {
            "models": {
                test_model: {
                    "description": "Test model for settings persistence",
                    "system_prompt": "Test system prompt",
                    "recommended_settings": test_settings
                }
            }
        }
        save_model_configs(new_config)
        print(f"   ✅ Test settings saved for {test_model}")
        
        # Reload and verify
        reloaded_configs = load_model_configs()
        reloaded_settings = reloaded_configs.get('models', {}).get(test_model, {}).get('recommended_settings', {})
        
        if reloaded_settings == test_settings:
            print(f"   ✅ Settings correctly reloaded: {reloaded_settings}")
        else:
            print(f"   ❌ Settings mismatch!")
            print(f"   Expected: {test_settings}")
            print(f"   Got: {reloaded_settings}")
            return False
            
    except Exception as e:
        print(f"   ❌ Failed to test settings save/load: {e}")
        return False
    
    # Test 4: Check API endpoints
    print("\n4. Testing API endpoints...")
    try:
        # Test favorites endpoint
        response = requests.get("http://localhost:8000/v1/config/favorites")
        if response.status_code == 200:
            api_favorites = response.json()
            print(f"   ✅ Favorites API working: {len(api_favorites.get('favorite_models', []))} models")
        else:
            print(f"   ❌ Favorites API failed: {response.status_code}")
            
        # Test model configs endpoint
        response = requests.get("http://localhost:8000/v1/config/models")
        if response.status_code == 200:
            api_configs = response.json()
            print(f"   ✅ Model configs API working: {len(api_configs.get('models', {}))} models")
        else:
            print(f"   ❌ Model configs API failed: {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("   ⚠️  API server not running, skipping API tests")
    except Exception as e:
        print(f"   ❌ API test failed: {e}")
    
    print("\n=== Settings Persistence Test Complete ===")
    return True

if __name__ == "__main__":
    success = test_settings_persistence()
    sys.exit(0 if success else 1) 