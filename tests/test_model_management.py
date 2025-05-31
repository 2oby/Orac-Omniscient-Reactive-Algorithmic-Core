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
import logging

logger = logging.getLogger(__name__)

@pytest.fixture
def llama_cpp_client():
    """Create a LlamaCppClient instance for testing."""
    model_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tests/test_models")
    return LlamaCppClient(model_path=model_path)

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
        response = await llama_cpp_client.generate(
            model=model,
            prompt=prompt,
            temperature=0.7,
            top_p=0.7,
            top_k=40,
            max_tokens=512,
            json_mode=False  # Ensure free-form text
        )
        
        # Print debug info
        print("\n=== Model Generation Test ===")
        print(f"Prompt: {prompt}")
        print(f"Response:\n{response.text}")
        print(f"Generation time: {response.response_time:.2f}s")
        print("===========================\n")
        
        # Verify response
        assert response.text, "Empty response from model"
        assert len(response.text.split('\n')) > 1, "Response too short"
        assert response.response_time > 0, "Invalid response time"
        assert response.model == model, "Model name mismatch"
        assert response.prompt == prompt, "Prompt mismatch"
        assert not response.json_mode, "JSON mode should be False"
        
    except Exception as e:
        if "libgomp.so.1" in str(e):
            pytest.skip("libgomp.so.1 not available")
        logger.error(f"Generation error: {str(e)}")
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