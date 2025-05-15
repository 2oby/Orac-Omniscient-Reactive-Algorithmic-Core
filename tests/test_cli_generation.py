import subprocess
import os
import pytest
import asyncio
from orac.llama_cpp_client import LlamaCppClient

@pytest.mark.asyncio
async def test_cli_generation():
    """Test model generation through the CLI with proper assertions"""
    # Initialize client to check model availability
    client = LlamaCppClient()
    models = await client.list_models()
    assert len(models) > 0, "No models found in /app/models/gguf"
    
    # Find the smallest model by file size using os module
    model_dir = "/app/models/gguf"
    files = []
    for filename in os.listdir(model_dir):
        if filename.endswith('.gguf'):
            filepath = os.path.join(model_dir, filename)
            size = os.path.getsize(filepath)
            files.append((size, filename))
    
    assert files, f"No .gguf files found in {model_dir}. Available files: {os.listdir(model_dir)}"
    smallest_model = min(files, key=lambda x: x[0])[1]
    print(f"\nFound {len(files)} models. Using smallest model: {smallest_model} ({files[0][0]/1024/1024:.1f}MB)")
    
    # Test generation through CLI
    prompt = "Write a haiku about AI running on a Jetson Orin"
    result = subprocess.run(
        ["python3", "-m", "orac.cli", "generate", 
         "--model", smallest_model,
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
    print(f"Model: {smallest_model}")
    print(f"Prompt: {prompt}")
    print(f"Response:\n{result.stdout}")
    print("=======================\n") 