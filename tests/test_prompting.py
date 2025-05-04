import pytest
import respx
from httpx import Response
from orac.ollama_client import OllamaClient
from orac.models import PromptRequest, PromptResponse

@pytest.fixture
def ollama_client():
    return OllamaClient()

@respx.mock
@pytest.mark.asyncio
async def test_prompt_success():
    # Mock successful prompt response
    expected_response = "Hello, I am an AI assistant."
    respx.post("http://orac-ollama:11434/api/generate").mock(
        return_value=Response(200, json={
            "response": expected_response,
            "done": True
        })
    )
    
    client = OllamaClient()
    response = await client.generate("Qwen3-0.6B-Q4_K_M", "Hello")
    assert response.response == expected_response
    assert response.elapsed_ms > 0

@respx.mock
@pytest.mark.asyncio
async def test_prompt_model_not_loaded():
    # Mock model not loaded error
    respx.post("http://orac-ollama:11434/api/generate").mock(
        return_value=Response(404, json={"error": "Model not loaded"})
    )
    
    client = OllamaClient()
    with pytest.raises(Exception) as exc_info:
        await client.generate("Qwen3-0.6B-Q4_K_M", "Hello")
    assert "Model not loaded" in str(exc_info.value)

@respx.mock
@pytest.mark.asyncio
async def test_prompt_empty_input():
    client = OllamaClient()
    with pytest.raises(ValueError) as exc_info:
        await client.generate("Qwen3-0.6B-Q4_K_M", "")
    assert "Prompt cannot be empty" in str(exc_info.value)

@respx.mock
@pytest.mark.asyncio
async def test_prompt_streaming():
    # Mock streaming response
    chunks = [
        '{"response": "Hello", "done": false}\n',
        '{"response": ", ", "done": false}\n',
        '{"response": "I am an AI", "done": false}\n',
        '{"response": " assistant.", "done": true}\n'
    ]
    
    async def stream_response(request):
        async def generate():
            for chunk in chunks:
                yield chunk.encode()
        
        return Response(200, content=generate())
    
    respx.post("http://orac-ollama:11434/api/generate").mock(side_effect=stream_response)
    
    client = OllamaClient()
    response = await client.generate("Qwen3-0.6B-Q4_K_M", "Hello", stream=True)
    assert response.response == "Hello, I am an AI assistant."
    assert response.elapsed_ms > 0 