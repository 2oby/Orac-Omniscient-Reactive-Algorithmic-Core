import pytest
import asyncio
from orac.ollama_client import OllamaClient
import time

MODELS = [
    "Qwen3-0.6B-Q4_K_M",
    "Qwen3-1.7B-Q4_K_M"
]

TEST_PROMPT = "What is the capital of France?"

@pytest.mark.asyncio
async def test_real_model_loading_and_prompting():
    client = OllamaClient()
    
    for model_name in MODELS:
        print(f"\nTesting model: {model_name}")
        
        # Test loading
        print("Loading model...")
        start_time = time.time()
        load_response = await client.load_model(model_name)
        load_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        print(f"Load time: {load_time:.2f}ms")
        assert load_response.status == "success"
        
        # Test prompting
        print("Sending prompt...")
        start_time = time.time()
        prompt_response = await client.generate(model_name, TEST_PROMPT)
        prompt_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        print(f"Response: {prompt_response.response}")
        print(f"Prompt time: {prompt_time:.2f}ms")
        assert prompt_response.response
        assert prompt_response.elapsed_ms > 0
        
        # Test unloading
        print("Unloading model...")
        start_time = time.time()
        unload_response = await client.unload_model(model_name)
        unload_time = (time.time() - start_time) * 1000  # Convert to milliseconds
        print(f"Unload time: {unload_time:.2f}ms")
        assert unload_response.status == "success"
        
        # Add a small delay between models
        await asyncio.sleep(1) 