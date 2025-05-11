import subprocess
import pytest
import asyncio
from orac.llama_cpp_client import LlamaCppClient

@pytest.mark.asyncio
async def test_cli_generation():
    """Test model generation through the CLI with proper assertions"""
    # Initialize client to check model availability
    client = LlamaCppClient()
    models = await client.list_models()
    assert len(models) > 0, "No models found"
    
    model_name = "Qwen3-0.6B-Q4_K_M.gguf"
    assert any(model["name"] == model_name for model in models), f"Model {model_name} not found"
    
    # Test generation through CLI
    prompt = "Write a haiku about AI running on a Jetson Orin"
    result = subprocess.run(
        ["python3", "-m", "orac.cli", "generate", 
         "--model", model_name,
         "--prompt", prompt],
        capture_output=True,
        text=True,
        check=True
    )
    
    # Verify output
    assert result.returncode == 0, f"CLI command failed: {result.stderr}"
    assert prompt in result.stdout, "Prompt not found in output"
    assert len(result.stdout.split('\n')) > 3, "Response too short"
    
    # Log the interaction for visibility
    print("\n=== Model Interaction ===")
    print(f"Prompt: {prompt}")
    print(f"Response:\n{result.stdout}")
    print("=======================\n") 