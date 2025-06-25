#!/usr/bin/env python3
"""
Test script to check if the web UI API endpoints are working correctly.
"""

import httpx
import json
import sys
import asyncio

async def test_api_endpoints():
    """Test the API endpoints used by the web UI."""
    
    base_url = "http://192.168.8.191:8000"
    
    print("=== Testing Web UI API Endpoints ===\n")
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        # Test 1: Models endpoint
        print("1. Testing /v1/models endpoint...")
        try:
            response = await client.get(f"{base_url}/v1/models")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                models = data.get('models', [])
                print(f"   Models found: {len(models)}")
                if models:
                    print(f"   First model: {models[0]['name']}")
                else:
                    print("   ⚠️  No models found!")
            else:
                print(f"   ❌ Error: {response.text}")
        except Exception as e:
            print(f"   ❌ Exception: {e}")
        
        print()
        
        # Test 2: Favorites endpoint
        print("2. Testing /v1/config/favorites endpoint...")
        try:
            response = await client.get(f"{base_url}/v1/config/favorites")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   Response: {json.dumps(data, indent=2)}")
            else:
                print(f"   ❌ Error: {response.text}")
        except Exception as e:
            print(f"   ❌ Exception: {e}")
        
        print()
        
        # Test 3: Model configs endpoint
        print("3. Testing /v1/config/models endpoint...")
        try:
            response = await client.get(f"{base_url}/v1/config/models")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   Response: {json.dumps(data, indent=2)}")
            else:
                print(f"   ❌ Error: {response.text}")
        except Exception as e:
            print(f"   ❌ Exception: {e}")
        
        print()
        
        # Test 4: Static files
        print("4. Testing static files...")
        try:
            response = await client.get(f"{base_url}/static/js/main.js")
            print(f"   JavaScript file status: {response.status_code}")
            if response.status_code == 200:
                print(f"   JavaScript file size: {len(response.text)} characters")
            else:
                print(f"   ❌ Error: {response.text}")
        except Exception as e:
            print(f"   ❌ Exception: {e}")
        
        try:
            response = await client.get(f"{base_url}/static/css/style.css")
            print(f"   CSS file status: {response.status_code}")
            if response.status_code == 200:
                print(f"   CSS file size: {len(response.text)} characters")
            else:
                print(f"   ❌ Error: {response.text}")
        except Exception as e:
            print(f"   ❌ Exception: {e}")
        
        print()
        
        # Test 5: Main page
        print("5. Testing main page...")
        try:
            response = await client.get(f"{base_url}/")
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                print(f"   Page size: {len(response.text)} characters")
                if "modelSelect" in response.text:
                    print("   ✅ Model select element found in HTML")
                else:
                    print("   ❌ Model select element NOT found in HTML")
            else:
                print(f"   ❌ Error: {response.text}")
        except Exception as e:
            print(f"   ❌ Exception: {e}")
        
        print("\n=== Test Complete ===")

if __name__ == "__main__":
    asyncio.run(test_api_endpoints()) 