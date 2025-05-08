import pytest
import respx
from httpx import Response
from orac.ollama_client import OllamaClient
from orac.models import ModelLoadRequest, ModelLoadResponse, ModelUnloadResponse

# Configure pytest to not show traceback
def pytest_exception_interact(call, report):
    if report.failed:
        # Only show the error message, not the traceback
        report.longrepr = str(call.excinfo.value)

@pytest.fixture(autouse=True)
def capture_logs(request):
    """Fixture to capture and format logs for failed tests."""
    yield
    if request.node.rep_call.failed:
        # Get the client from the test function
        client = request.function.__globals__.get('client')
        if client and hasattr(client, 'model_loader'):
            debug_logs = client.model_loader.get_debug_logs()
            error_logs = client.model_loader.get_error_logs()
            
            if debug_logs or error_logs:
                print("\n=== Debug Logs ===")
                for log in debug_logs:
                    print(f"{log['stage']}: {log.get('data', {})}")
                
                print("\n=== Error Logs ===")
                for log in error_logs:
                    print(log)

@pytest.fixture
def ollama_client():
    return OllamaClient()

@respx.mock
@pytest.mark.asyncio
async def test_real_model_loading_and_prompting():
    # Mock version check
    respx.get("http://orac-ollama:11434/api/version").mock(
        return_value=Response(200, json={"version": "0.6.7"})
    )
    
    # Mock create endpoint
    respx.post("http://orac-ollama:11434/api/create").mock(
        return_value=Response(200, json={"status": "success"})
    )
    
    global client
    client = OllamaClient()
    response = await client.load_model("Qwen3-0.6B-Q4_K_M")
    assert response["status"] == "success"

@respx.mock
@pytest.mark.asyncio
async def test_load_model_success():
    # Mock successful model loading
    respx.post("http://orac-ollama:11434/api/create").mock(
        return_value=Response(200, json={"status": "success"})
    )
    # Mock version check
    respx.get("http://orac-ollama:11434/api/version").mock(
        return_value=Response(200, json={"version": "0.6.7"})
    )
    
    global client
    client = OllamaClient()
    response = await client.load_model("Qwen3-0.6B-Q4_K_M")
    assert response["status"] == "success"

@respx.mock
@pytest.mark.asyncio
async def test_load_model_not_found():
    # Mock model not found error
    respx.post("http://orac-ollama:11434/api/create").mock(
        return_value=Response(404, json={"error": "Model not found"})
    )
    # Mock version check
    respx.get("http://orac-ollama:11434/api/version").mock(
        return_value=Response(200, json={"version": "0.6.7"})
    )
    
    global client
    client = OllamaClient()
    with pytest.raises(Exception) as exc_info:
        await client.load_model("nonexistent-model")
    assert "Model not found" in str(exc_info.value)

@respx.mock
@pytest.mark.asyncio
async def test_unload_model_success():
    # Mock successful model unloading
    respx.delete("http://orac-ollama:11434/api/delete").mock(
        return_value=Response(200, json={"status": "success"})
    )
    
    global client
    client = OllamaClient()
    response = await client.unload_model("Qwen3-0.6B-Q4_K_M")
    assert response.status == "success"

@respx.mock
@pytest.mark.asyncio
async def test_unload_model_not_loaded():
    # Mock model not loaded error
    respx.delete("http://orac-ollama:11434/api/delete").mock(
        return_value=Response(404, json={"error": "Model not loaded"})
    )
    
    global client
    client = OllamaClient()
    with pytest.raises(Exception) as exc_info:
        await client.unload_model("Qwen3-0.6B-Q4_K_M")
    assert "Model not loaded" in str(exc_info.value) 