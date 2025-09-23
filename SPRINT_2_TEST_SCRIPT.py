#!/usr/bin/env python3
"""
Sprint 2 Test Script - Device Type + Location Mapping System
Tests the implementation of Sprint 2 with Home Assistant integration
"""

import requests
import json
import time
from typing import Dict, List, Optional
import sys
from datetime import datetime

# Configuration
ORAC_BASE_URL = "http://192.168.8.192:8000"
HA_URL = "http://192.168.8.99"  # Your Home Assistant URL
HA_PORT = 8123
HA_TOKEN = ""  # Will need to be provided

# Test results collector
test_results = {
    "passed": [],
    "failed": [],
    "skipped": []
}

def log_test(test_name: str, status: str, message: str = ""):
    """Log test result"""
    timestamp = datetime.now().strftime("%H:%M:%S")
    status_symbol = "✓" if status == "PASS" else "✗" if status == "FAIL" else "⊙"
    print(f"[{timestamp}] {status_symbol} {test_name}: {status} {message}")

    if status == "PASS":
        test_results["passed"].append(test_name)
    elif status == "FAIL":
        test_results["failed"].append(f"{test_name}: {message}")
    else:
        test_results["skipped"].append(f"{test_name}: {message}")

def test_api_availability():
    """Test 1: Check if ORAC API is accessible"""
    try:
        response = requests.get(f"{ORAC_BASE_URL}/api/backends", timeout=5)
        if response.status_code == 200:
            log_test("API Availability", "PASS")
            return True
        else:
            log_test("API Availability", "FAIL", f"Status code: {response.status_code}")
            return False
    except Exception as e:
        log_test("API Availability", "FAIL", str(e))
        return False

def test_list_backends():
    """Test 2: List existing backends"""
    try:
        response = requests.get(f"{ORAC_BASE_URL}/api/backends")
        if response.status_code == 200:
            data = response.json()
            backends = data.get("backends", [])
            log_test("List Backends", "PASS", f"Found {len(backends)} backend(s)")
            return backends
        else:
            log_test("List Backends", "FAIL", f"Status code: {response.status_code}")
            return []
    except Exception as e:
        log_test("List Backends", "FAIL", str(e))
        return []

def test_create_backend(name: str, ha_token: str):
    """Test 3: Create a new Home Assistant backend"""
    backend_data = {
        "name": name,
        "type": "homeassistant",
        "connection": {
            "url": HA_URL,
            "port": HA_PORT,
            "token": ha_token
        }
    }

    try:
        response = requests.post(
            f"{ORAC_BASE_URL}/api/backends",
            json=backend_data,
            timeout=10
        )

        if response.status_code in [200, 201]:
            data = response.json()
            backend_id = data.get("backend", {}).get("id")
            log_test("Create Backend", "PASS", f"Backend ID: {backend_id}")
            return backend_id
        else:
            log_test("Create Backend", "FAIL", f"Status code: {response.status_code}")
            return None
    except Exception as e:
        log_test("Create Backend", "FAIL", str(e))
        return None

def test_backend_structure(backend_id: str):
    """Test 4: Verify Sprint 2 backend structure"""
    try:
        response = requests.get(f"{ORAC_BASE_URL}/api/backends/{backend_id}")
        if response.status_code == 200:
            data = response.json().get("backend", {})

            # Check for Sprint 2 fields
            required_fields = ["device_mappings", "device_types", "locations"]
            missing_fields = [f for f in required_fields if f not in data]

            if not missing_fields:
                log_test("Backend Structure", "PASS", "All Sprint 2 fields present")

                # Check default device types
                device_types = data.get("device_types", [])
                expected_types = ["lights", "heating", "media_player", "blinds", "switches"]
                if all(dt in device_types for dt in expected_types):
                    log_test("Default Device Types", "PASS", f"Found {len(device_types)} device types")
                else:
                    log_test("Default Device Types", "FAIL", f"Missing some default types")

                return True
            else:
                log_test("Backend Structure", "FAIL", f"Missing fields: {missing_fields}")
                return False
        else:
            log_test("Backend Structure", "FAIL", f"Status code: {response.status_code}")
            return False
    except Exception as e:
        log_test("Backend Structure", "FAIL", str(e))
        return False

def test_connection(backend_id: str):
    """Test 5: Test Home Assistant connection"""
    try:
        response = requests.post(
            f"{ORAC_BASE_URL}/api/backends/{backend_id}/test",
            timeout=10
        )

        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success":
                entity_count = data.get("entity_count", 0)
                log_test("HA Connection Test", "PASS", f"Found {entity_count} entities")
                return True
            else:
                log_test("HA Connection Test", "FAIL", data.get("message", "Unknown error"))
                return False
        else:
            log_test("HA Connection Test", "FAIL", f"Status code: {response.status_code}")
            return False
    except Exception as e:
        log_test("HA Connection Test", "FAIL", str(e))
        return False

def test_fetch_entities(backend_id: str):
    """Test 6: Fetch entities from Home Assistant"""
    try:
        response = requests.post(
            f"{ORAC_BASE_URL}/api/backends/{backend_id}/entities/fetch",
            timeout=30
        )

        if response.status_code == 200:
            data = response.json()
            total_entities = data.get("total_entities", 0)
            locations = data.get("locations", [])

            log_test("Fetch Entities", "PASS",
                    f"Fetched {total_entities} entities, {len(locations)} locations")

            # Check if locations were extracted from HA areas
            if locations:
                log_test("Location Extraction", "PASS", f"Locations: {', '.join(locations[:5])}")
            else:
                log_test("Location Extraction", "SKIP", "No locations found in HA")

            return total_entities > 0
        else:
            log_test("Fetch Entities", "FAIL", f"Status code: {response.status_code}")
            return False
    except Exception as e:
        log_test("Fetch Entities", "FAIL", str(e))
        return False

def test_device_mapping(backend_id: str):
    """Test 7: Test device mapping functionality"""
    try:
        # First, get the list of entities
        response = requests.get(f"{ORAC_BASE_URL}/api/backends/{backend_id}/entities")
        if response.status_code != 200:
            log_test("Get Entities", "FAIL", f"Status code: {response.status_code}")
            return False

        entities = response.json().get("entities", {})
        if not entities:
            log_test("Device Mapping", "SKIP", "No entities to map")
            return False

        # Pick the first entity to test mapping
        first_entity_id = list(entities.keys())[0]

        # Create a device mapping
        mapping_data = {
            "enabled": True,
            "device_type": "lights",
            "location": "test_room"
        }

        response = requests.put(
            f"{ORAC_BASE_URL}/api/backends/{backend_id}/entities/{first_entity_id}",
            json=mapping_data
        )

        if response.status_code == 200:
            log_test("Create Device Mapping", "PASS",
                    f"Mapped {first_entity_id} as lights in test_room")

            # Verify the mapping was saved
            response = requests.get(f"{ORAC_BASE_URL}/api/backends/{backend_id}")
            backend_data = response.json().get("backend", {})
            device_mappings = backend_data.get("device_mappings", {})

            if first_entity_id in device_mappings:
                mapping = device_mappings[first_entity_id]
                if (mapping.get("device_type") == "lights" and
                    mapping.get("location") == "test_room"):
                    log_test("Verify Mapping", "PASS", "Mapping correctly saved")
                    return True
                else:
                    log_test("Verify Mapping", "FAIL", "Mapping data incorrect")
                    return False
            else:
                log_test("Verify Mapping", "FAIL", "Mapping not found in backend data")
                return False
        else:
            log_test("Create Device Mapping", "FAIL", f"Status code: {response.status_code}")
            return False
    except Exception as e:
        log_test("Device Mapping", "FAIL", str(e))
        return False

def test_duplicate_validation(backend_id: str):
    """Test 8: Test duplicate Type + Location validation"""
    try:
        # Get entities
        response = requests.get(f"{ORAC_BASE_URL}/api/backends/{backend_id}/entities")
        entities = response.json().get("entities", {})

        if len(entities) < 2:
            log_test("Duplicate Validation", "SKIP", "Need at least 2 entities")
            return False

        entity_ids = list(entities.keys())[:2]

        # Map first entity
        mapping_data = {
            "enabled": True,
            "device_type": "lights",
            "location": "duplicate_test_room"
        }

        response = requests.put(
            f"{ORAC_BASE_URL}/api/backends/{backend_id}/entities/{entity_ids[0]}",
            json=mapping_data
        )

        if response.status_code != 200:
            log_test("Duplicate Validation Setup", "FAIL", "Could not set up first mapping")
            return False

        # Try to map second entity with same Type + Location
        response = requests.put(
            f"{ORAC_BASE_URL}/api/backends/{backend_id}/entities/{entity_ids[1]}",
            json=mapping_data
        )

        # This should fail or return a validation error
        if response.status_code == 400:
            log_test("Duplicate Validation", "PASS", "Correctly prevented duplicate mapping")
            return True
        elif response.status_code == 200:
            # Check if there's a validation warning in the response
            data = response.json()
            if "warning" in data or "conflict" in data:
                log_test("Duplicate Validation", "PASS", "Warning about duplicate mapping")
                return True
            else:
                log_test("Duplicate Validation", "FAIL", "Duplicate mapping allowed without warning")
                return False
        else:
            log_test("Duplicate Validation", "FAIL", f"Unexpected status: {response.status_code}")
            return False
    except Exception as e:
        log_test("Duplicate Validation", "FAIL", str(e))
        return False

def test_custom_locations(backend_id: str):
    """Test 9: Test adding custom locations"""
    try:
        custom_location = f"custom_room_{int(time.time())}"

        response = requests.post(
            f"{ORAC_BASE_URL}/api/backends/{backend_id}/locations",
            json={"location": custom_location}
        )

        if response.status_code in [200, 201]:
            log_test("Add Custom Location", "PASS", f"Added: {custom_location}")

            # Verify it was added
            response = requests.get(f"{ORAC_BASE_URL}/api/backends/{backend_id}")
            backend_data = response.json().get("backend", {})
            locations = backend_data.get("locations", [])

            if custom_location in locations:
                log_test("Verify Custom Location", "PASS", "Location persisted")
                return True
            else:
                log_test("Verify Custom Location", "FAIL", "Location not found in backend")
                return False
        else:
            log_test("Add Custom Location", "FAIL", f"Status code: {response.status_code}")
            return False
    except Exception as e:
        log_test("Custom Locations", "FAIL", str(e))
        return False

def test_custom_device_types(backend_id: str):
    """Test 10: Test adding custom device types"""
    try:
        custom_type = f"custom_device_{int(time.time())}"

        response = requests.post(
            f"{ORAC_BASE_URL}/api/backends/{backend_id}/device-types",
            json={"device_type": custom_type}
        )

        if response.status_code in [200, 201]:
            log_test("Add Custom Device Type", "PASS", f"Added: {custom_type}")

            # Verify it was added
            response = requests.get(f"{ORAC_BASE_URL}/api/backends/{backend_id}")
            backend_data = response.json().get("backend", {})
            device_types = backend_data.get("device_types", [])

            if custom_type in device_types:
                log_test("Verify Custom Device Type", "PASS", "Device type persisted")
                return True
            else:
                log_test("Verify Custom Device Type", "FAIL", "Device type not found")
                return False
        else:
            log_test("Add Custom Device Type", "FAIL", f"Status code: {response.status_code}")
            return False
    except Exception as e:
        log_test("Custom Device Types", "FAIL", str(e))
        return False

def print_summary():
    """Print test summary"""
    print("\n" + "="*60)
    print("SPRINT 2 TEST SUMMARY")
    print("="*60)

    total = len(test_results["passed"]) + len(test_results["failed"]) + len(test_results["skipped"])

    print(f"\n✓ PASSED: {len(test_results['passed'])}/{total}")
    for test in test_results["passed"]:
        print(f"  • {test}")

    if test_results["failed"]:
        print(f"\n✗ FAILED: {len(test_results['failed'])}/{total}")
        for test in test_results["failed"]:
            print(f"  • {test}")

    if test_results["skipped"]:
        print(f"\n⊙ SKIPPED: {len(test_results['skipped'])}/{total}")
        for test in test_results["skipped"]:
            print(f"  • {test}")

    print("\n" + "="*60)

    if not test_results["failed"]:
        print("🎉 All tests passed! Sprint 2 implementation is working correctly.")
    else:
        print("⚠️  Some tests failed. Please review the failures above.")

    print("="*60)

def main():
    """Main test runner"""
    print("="*60)
    print("SPRINT 2 TEST SUITE - Device Type + Location Mapping")
    print("="*60)
    print(f"Testing ORAC at: {ORAC_BASE_URL}")
    print(f"Home Assistant at: {HA_URL}:{HA_PORT}")
    print("="*60 + "\n")

    # Check if HA token is provided
    if not HA_TOKEN:
        print("⚠️  Home Assistant token not set in the script.")
        print("Please edit this script and set the HA_TOKEN variable.")
        print("You can get a token from HA: Profile > Long-Lived Access Tokens")
        return

    # Run tests
    if not test_api_availability():
        print("\n❌ ORAC API is not accessible. Please check if the container is running.")
        return

    backends = test_list_backends()

    # Create a test backend
    backend_name = f"Sprint2_Test_{int(time.time())}"
    backend_id = test_create_backend(backend_name, HA_TOKEN)

    if not backend_id:
        print("\n❌ Could not create backend. Check your HA token and connection.")
        return

    print(f"\n📋 Testing with backend: {backend_id}\n")

    # Run Sprint 2 specific tests
    test_backend_structure(backend_id)

    if test_connection(backend_id):
        test_fetch_entities(backend_id)
        test_device_mapping(backend_id)
        test_duplicate_validation(backend_id)
        test_custom_locations(backend_id)
        test_custom_device_types(backend_id)

    # Print summary
    print_summary()

if __name__ == "__main__":
    main()