"""
Tests for the API endpoints.

These tests verify that the API endpoints function correctly, including JSON generation.
"""

import pytest
from fastapi.testclient import TestClient
import json
from orac.api import app
from orac.models import GenerationRequest

# Create a test client
client = TestClient(app)

def test_generate_json_response():
    """Test that the API generates a valid JSON response for a home automation command."""
    # Test data
    test_data = {
        "model": "Qwen3-0.6B-Q4_K_M.gguf",  # Using our smallest model for testing
        "prompt": "turn on the bathroom lights",
        "json_mode": True,
        "temperature": 0.2,
        "top_p": 0.8,
        "top_k": 30,
        "max_tokens": 50
    }
    
    # Make the request
    response = client.post("/v1/generate", json=test_data)
    
    # Print debug info
    print("\n=== API JSON Generation Test ===")
    print(f"Request: {json.dumps(test_data, indent=2)}")
    print(f"Response status: {response.status_code}")
    print(f"Response body: {response.text}")
    print("==============================\n")
    
    # Verify response
    assert response.status_code == 200, f"API request failed with status {response.status_code}: {response.text}"
    
    # Parse response
    result = response.json()
    assert result["status"] == "success", f"Generation failed: {result.get('error', 'Unknown error')}"
    assert result["response"], "Empty response from model"
    
    # Parse the JSON response from the model
    try:
        model_response = json.loads(result["response"])
        # Verify JSON structure
        assert isinstance(model_response, dict), "Response is not a JSON object"
        assert "device" in model_response, "Missing 'device' in JSON response"
        assert "action" in model_response, "Missing 'action' in JSON response"
        assert "location" in model_response, "Missing 'location' in JSON response"
        
        # Verify content
        assert model_response["action"].lower() in ["turn on", "turn off", "toggle"], "Invalid action in response"
        assert "light" in model_response["device"].lower(), "Device should be a light"
        assert "bathroom" in model_response["location"].lower(), "Location should be bathroom"
        
    except json.JSONDecodeError as e:
        pytest.fail(f"Invalid JSON in model response: {e}")
    
    # Verify metadata
    assert result["elapsed_ms"] > 0, "Invalid response time"
    assert result["model"] == test_data["model"], "Model name mismatch" 