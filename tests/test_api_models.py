"""
Tests for the API endpoints.
"""

import pytest
from fastapi.testclient import TestClient
import os
from pathlib import Path

from orac.api import app

client = TestClient(app)

def test_list_models_endpoint():
    """Test the list models endpoint."""
    resp = client.get("/v1/models")
    assert resp.status_code == 200
    
    data = resp.json()
    assert "models" in data
    assert isinstance(data["models"], list)
    
    # Check each model has the required fields
    for model in data["models"]:
        assert "name" in model
        assert "size" in model
        assert "modified" in model
        assert "backend" in model
        assert model["backend"] == "llama_cpp"
        
        # Verify the model file exists
        model_path = os.path.join("/models/gguf", model["name"])
        assert os.path.exists(model_path)
        assert os.path.getsize(model_path) == model["size"]

def test_generate_endpoint():
    """Test the generate endpoint."""
    # Get a model to test with
    models_resp = client.get("/v1/models")
    assert models_resp.status_code == 200
    models = models_resp.json()["models"]
    if not models:
        pytest.skip("No models available for testing")
    
    # Use the specific model we want to test
    model = "Qwen3-0.6B-Q4_K_M.gguf"
    
    # Verify the model exists
    if not any(m["name"] == model for m in models):
        pytest.skip(f"Required model {model} not found")
    
    prompt = "Write a haiku about artificial intelligence."
    
    resp = client.post("/v1/generate", json={
        "model": model,
        "prompt": prompt,
        "stream": False
    })
    
    assert resp.status_code == 200
    data = resp.json()
    assert "response" in data
    assert len(data["response"]) > 0
    assert "elapsed_ms" in data
    assert data["elapsed_ms"] > 0

def test_healthcheck_endpoint():
    """Test the health check endpoint."""
    resp = client.get("/healthz")
    assert resp.status_code == 200
    
    data = resp.json()
    assert "status" in data
    assert data["status"] in ["healthy", "unhealthy"]
    assert "models_count" in data
    assert isinstance(data["models_count"], int)
