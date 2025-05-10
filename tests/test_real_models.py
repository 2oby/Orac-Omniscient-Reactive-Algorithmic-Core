"""
Tests for real model interaction using llama.cpp.

These tests verify that the llama.cpp client can interact with actual models
on the system. They require model files to be present in the models directory.
"""

import os
import pytest
import asyncio
from typing import List

from orac.llama_cpp_client import LlamaCppClient

# List of models to test
MODELS = [
    "Qwen3-0.6B-Q4_K_M.gguf",  # Primary test model
    "Qwen3-1.7B-Q4_K_M.gguf",  # Optional larger model
]

async def wait_for_llama_cpp(client: LlamaCppClient, max_retries: int = 5) -> bool:
    """Wait for llama.cpp to be ready."""
    for i in range(max_retries):
        try:
            await client.list_models()
            return True
        except Exception:
            if i < max_retries - 1:
                await asyncio.sleep(1)
    return False

@pytest.mark.asyncio
async def test_real_model_loading_and_prompting():
    client = LlamaCppClient()

    # Check if models directory exists and contains the expected files
    models_dir = "/models/gguf"
    if not os.path.exists(models_dir):
        pytest.skip(f"Models directory {models_dir} not found. Please ensure models are mounted correctly.")
    
    missing_models = []
    for model in MODELS:
        model_path = os.path.join(models_dir, model)
        if not os.path.exists(model_path):
            missing_models.append(model)
    
    if missing_models:
        pytest.skip(f"Some model files are missing: {', '.join(missing_models)}. Please ensure all models are present in {models_dir}")
    
    # Test each model
    for model in MODELS:
        # Test model listing
        models = await client.list_models()
        assert any(m["name"] == model for m in models), f"Model {model} not found in list"
        
        # Test generation
        prompt = "Write a haiku about artificial intelligence."
        response = await client.generate(model, prompt)
        assert response.response, "No response generated"
        assert len(response.response) > 0, "Empty response generated"
        assert response.elapsed_ms > 0, "Invalid elapsed time" 