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
    
    # Find the smallest Qwen3 model by file size
    model_dir = "/app/models/gguf"
    files = []
    for filename in os.listdir(model_dir):
        if filename.endswith('.gguf') and 'Qwen3' in filename:  # Prefer Qwen3 models
            filepath = os.path.join(model_dir, filename)
            size = os.path.getsize(filepath)
            files.append((size, filename))
    
    # If no Qwen3 models found, fall back to any model
    if not files:
        print("No Qwen3 models found, falling back to any available model")
        for filename in os.listdir(model_dir):
            if filename.endswith('.gguf'):
                filepath = os.path.join(model_dir, filename)
                size = os.path.getsize(filepath)
                files.append((size, filename))
    
    assert files, f"No .gguf files found in {model_dir}. Available files: {os.listdir(model_dir)}"
    smallest_model = min(files, key=lambda x: x[0])[1]
    print(f"\nFound {len(files)} models. Using smallest model: {smallest_model} ({files[0][0]/1024/1024:.1f}MB)")
    
    # Test generation through CLI with system prompt
    system_prompt = "You are a helpful AI assistant running on a Jetson Orin. Write concise, creative responses."
    user_prompt = "Write a haiku about AI running on a Jetson Orin"
    
    result = subprocess.run(
        ["python3", "-m", "orac.cli", "generate", 
         "--model", smallest_model,
         "--system-prompt", system_prompt,
         "--prompt", user_prompt],
        capture_output=True,
        text=True,
        check=True
    )
    
    # Verify output
    assert result.returncode == 0, f"CLI command failed: {result.stderr}"
    assert user_prompt in result.stdout, "Prompt not found in output"
    assert len(result.stdout.split('\n')) > 3, "Response too short"
    
    # Log the interaction for visibility
    print("\n=== Model Interaction ===")
    print(f"Model: {smallest_model}")
    print(f"System Prompt: {system_prompt}")
    print(f"User Prompt: {user_prompt}")
    print(f"Response:\n{result.stdout}")
    print("=======================\n") 