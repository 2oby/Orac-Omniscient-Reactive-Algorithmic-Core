"""
Tests for text generation functionality.
"""

import pytest
from orac.llama_cpp_client import LlamaCppClient

@pytest.fixture
def llama_cpp_client():
    """Create a LlamaCppClient instance for testing."""
    return LlamaCppClient()

@pytest.mark.asyncio
async def test_generate_text(llama_cpp_client):
    """Test text generation with a model."""
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
    response = await llama_cpp_client.generate(model, prompt)
    
    assert response.response
    assert len(response.response) > 0
    assert response.elapsed_ms > 0
    assert response.model == model
    assert response.prompt == prompt 