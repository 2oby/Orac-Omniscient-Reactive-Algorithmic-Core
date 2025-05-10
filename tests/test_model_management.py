"""
Tests for model interaction using llama.cpp CLI.

These tests verify that we can:
1. List available models
2. Generate text using llama-cli
3. Handle errors appropriately
"""

import pytest
import os
from pathlib import Path
from orac.llama_cpp_client import LlamaCppClient

@pytest.fixture
def llama_cpp_client():
    """Create a LlamaCppClient instance for testing."""
    return LlamaCppClient()

@pytest.mark.asyncio
async def test_list_models(llama_cpp_client):
    """Test listing available models."""
    models = await llama_cpp_client.list_models()
    assert isinstance(models, list)
    for model in models:
        assert "name" in model
        assert "size" in model
        assert "modified" in model
        assert "backend" in model
        assert model["backend"] == "llama_cpp"

@pytest.mark.asyncio
async def test_generate_with_real_model(llama_cpp_client):
    """Test text generation with a real model using llama-cli."""
    # Skip if no models are available
    models = await llama_cpp_client.list_models()
    if not models:
        pytest.skip("No models available for testing")
    
    # Use the specific model we want to test
    model = "Qwen3-0.6B-Q4_K_M.gguf"
    
    # Verify the model exists
    if not any(m["name"] == model for m in models):
        pytest.skip(f"Required model {model} not found")
    
    # Test generation
    prompt = "Write a haiku about artificial intelligence."
    try:
        response = await llama_cpp_client.generate(model, prompt)
        assert response.response
        assert len(response.response) > 0
        assert response.elapsed_ms > 0
        assert response.model == model
        assert response.prompt == prompt
    except Exception as e:
        if "libgomp.so.1" in str(e):
            pytest.skip("libgomp.so.1 not available")
        raise

@pytest.mark.asyncio
async def test_generate_with_nonexistent_model(llama_cpp_client):
    """Test that generating with a nonexistent model raises an error."""
    with pytest.raises(FileNotFoundError) as exc_info:
        await llama_cpp_client.generate("nonexistent-model.gguf", "test prompt")
    assert "Model not found" in str(exc_info.value)

@pytest.mark.asyncio
async def test_generate_with_empty_prompt(llama_cpp_client):
    """Test that generating with an empty prompt raises an error."""
    with pytest.raises(ValueError) as exc_info:
        await llama_cpp_client.generate("test-model.gguf", "")
    assert "Prompt cannot be empty" in str(exc_info.value) 