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
        check=False  # Don't check return code yet
    )
    
    # Print debug info
    print("\n=== CLI Command Output ===")
    print(f"Return code: {result.returncode}")
    print(f"stdout:\n{result.stdout}")
    print(f"stderr:\n{result.stderr}")
    print("========================\n")
    
    # Verify output
    assert result.returncode == 0, f"CLI command failed with code {result.returncode}: {result.stderr}"
    
    # Look for the response in the output
    # The response should be after "Generated response:" and before any error messages
    output_lines = result.stdout.split('\n')
    response_start = -1
    for i, line in enumerate(output_lines):
        if "Generated response:" in line:
            response_start = i + 1
            break
    
    assert response_start >= 0, "Could not find 'Generated response:' in output"
    response = '\n'.join(output_lines[response_start:]).strip()
    assert response, "Empty response from model"
    assert len(response.split('\n')) > 1, "Response too short"
    
    # Log the interaction for visibility
    print("\n=== Model Interaction ===")
    print(f"Prompt: {prompt}")
    print(f"Response:\n{response}")
    print("=======================\n") 