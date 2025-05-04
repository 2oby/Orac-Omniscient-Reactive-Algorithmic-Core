import pytest
import asyncio
import time
from orac.ollama_client import OllamaClient
import httpx

MODELS = [
    "Qwen3-0.6B-Q4_K_M",
    "Qwen3-1.7B-Q4_K_M"
]

TEST_PROMPT = "What is the capital of France?"

async def wait_for_ollama(client: OllamaClient, max_retries: int = 5, delay: float = 2.0) -> bool:
    """Wait for Ollama to be ready."""
    for i in range(max_retries):
        try:
            await client.list_models()
            return True
        except httpx.ConnectError:
            if i < max_retries - 1:
                print(f"Waiting for Ollama to be ready... (attempt {i + 1}/{max_retries})")
                await asyncio.sleep(delay)
            else:
                return False
    return False

@pytest.mark.asyncio
async def test_real_model_loading_and_prompting():
    client = OllamaClient()
    
    # Wait for Ollama to be ready
    if not await wait_for_ollama(client):
        pytest.fail("Could not connect to Ollama server after multiple attempts")
    
    for model_name in MODELS:
        print(f"\nTesting model: {model_name}")
        
        try:
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
            
        except Exception as e:
            pytest.fail(f"Test failed for model {model_name}: {str(e)}")
        finally:
            # Add a small delay between models
            await asyncio.sleep(1)
    
    await client.close() 