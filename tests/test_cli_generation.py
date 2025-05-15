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
    assert len(models) > 0, "No models found in /app/models/gguf"
    
    # Find the smallest model by file size
    ls_result = subprocess.run(
        ["ls", "-l", "/app/models/gguf/*.gguf"],
        capture_output=True,
        text=True,
        shell=True,
        check=True
    )
    
    # Parse ls output to find smallest file
    files = []
    for line in ls_result.stdout.split('\n'):
        if line.strip() and '.gguf' in line:
            parts = line.split()
            if len(parts) >= 9:  # ls -l output has at least 9 fields
                size = int(parts[4])
                name = parts[-1].split('/')[-1]  # Get just the filename
                files.append((size, name))
    
    assert files, "No .gguf files found in /app/models/gguf"
    smallest_model = min(files, key=lambda x: x[0])[1]
    print(f"\nFound {len(files)} models. Using smallest model: {smallest_model} ({smallest_model[0]/1024/1024:.1f}MB)")
    
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