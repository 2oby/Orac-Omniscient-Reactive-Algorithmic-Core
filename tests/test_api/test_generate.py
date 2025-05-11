import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from orac.api.main import app
from orac.api.models.schemas import GenerationRequest

client = TestClient(app)

def test_generate_endpoint():
    """Test the text generation endpoint."""
    request_data = {
        "prompt": "Write a short poem about AI",
        "model": "Qwen3-0.6B-Q4_K_M.gguf",
        "temperature": 0.7,
        "max_tokens": 100,
        "top_p": 0.7,
        "top_k": 40
    }
    
    response = client.post("/api/v1/generate", json=request_data)
    assert response.status_code == 200
    
    data = response.json()
    assert "generated_text" in data
    assert "model" in data
    assert "prompt" in data
    assert "parameters" in data
    assert "elapsed_ms" in data
    assert data["model"] == request_data["model"]
    assert data["prompt"] == request_data["prompt"]
    assert isinstance(data["elapsed_ms"], float)
    assert data["parameters"]["temperature"] == request_data["temperature"]
    assert data["parameters"]["max_tokens"] == request_data["max_tokens"]
    assert data["parameters"]["top_p"] == request_data["top_p"]
    assert data["parameters"]["top_k"] == request_data["top_k"]

def test_generate_invalid_model():
    """Test generation with a non-existent model."""
    request_data = {
        "prompt": "Write a short poem about AI",
        "model": "non_existent_model.gguf",
        "temperature": 0.7,
        "max_tokens": 100,
        "top_p": 0.7,
        "top_k": 40
    }
    
    response = client.post("/api/v1/generate", json=request_data)
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

def test_generate_invalid_parameters():
    """Test generation with invalid parameters."""
    request_data = {
        "prompt": "Write a short poem about AI",
        "model": "Qwen3-0.6B-Q4_K_M.gguf",
        "temperature": 2.0,  # Invalid temperature
        "max_tokens": 100,
        "top_p": 0.7,
        "top_k": 40
    }
    
    response = client.post("/api/v1/generate", json=request_data)
    assert response.status_code == 422  # Validation error 

@patch('orac.api.routes.generate.client')
def test_generate_model_failure(mock_client):
    """Test generation when the model fails to generate."""
    # Setup mock to simulate model failure
    mock_client.model_exists.return_value = True
    mock_client.generate.side_effect = Exception("Model generation failed")
    
    request_data = {
        "prompt": "Write a short poem about AI",
        "model": "Qwen3-0.6B-Q4_K_M.gguf",
        "temperature": 0.7,
        "max_tokens": 100,
        "top_p": 0.7,
        "top_k": 40
    }
    
    response = client.post("/api/v1/generate", json=request_data)
    assert response.status_code == 500
    assert "Model generation failed" in response.json()["detail"]

@patch('orac.api.routes.generate.client')
def test_generate_invalid_response_format(mock_client):
    """Test generation when the model returns invalid response format."""
    # Setup mock to return non-string response
    mock_client.model_exists.return_value = True
    mock_client.generate.return_value = {"text": "invalid format"}
    
    request_data = {
        "prompt": "Write a short poem about AI",
        "model": "Qwen3-0.6B-Q4_K_M.gguf",
        "temperature": 0.7,
        "max_tokens": 100,
        "top_p": 0.7,
        "top_k": 40
    }
    
    response = client.post("/api/v1/generate", json=request_data)
    assert response.status_code == 500
    assert "invalid response format" in response.json()["detail"].lower() 