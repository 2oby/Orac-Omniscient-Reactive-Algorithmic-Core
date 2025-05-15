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
    
    # Find a suitable model for testing
    model_dir = "/app/models/gguf"
    files = []
    for filename in os.listdir(model_dir):
        if filename.endswith('.gguf'):
            filepath = os.path.join(model_dir, filename)
            size = os.path.getsize(filepath)
            # Prefer Qwen3 models, but accept any valid model
            if 'Qwen3' in filename:
                files.append((size, filename, True))  # True indicates Qwen3 model
            else:
                files.append((size, filename, False))
    
    assert files, f"No .gguf files found in {model_dir}. Available files: {os.listdir(model_dir)}"
    
    # First try to find the smallest Qwen3 model
    qwen_models = [f for f in files if f[2]]
    if qwen_models:
        test_model = min(qwen_models, key=lambda x: x[0])[1]
        print(f"\nFound {len(qwen_models)} Qwen3 models. Using smallest: {test_model} ({min(qwen_models)[0]/1024/1024:.1f}MB)")
    else:
        # Fall back to any model if no Qwen3 models found
        test_model = min(files, key=lambda x: x[0])[1]
        print(f"\nNo Qwen3 models found. Using smallest available model: {test_model} ({min(files)[0]/1024/1024:.1f}MB)")
    
    # Test generation through CLI
    user_prompt = "Write a haiku about AI running on a Jetson Orin"
    
    try:
        result = subprocess.run(
            ["python3", "-m", "orac.cli", "generate", 
             "--model", test_model,
             "--prompt", user_prompt],
            capture_output=True,
            text=True,
            check=True,
            timeout=30  # Add timeout to prevent hanging
        )
        
        # Verify output
        assert result.returncode == 0, f"CLI command failed: {result.stderr}"
        assert user_prompt in result.stdout, "Prompt not found in output"
        assert len(result.stdout.split('\n')) > 3, "Response too short"
        
        # Log the interaction for visibility
        print("\n=== Model Interaction ===")
        print(f"Model: {test_model}")
        print(f"User Prompt: {user_prompt}")
        print(f"Response:\n{result.stdout}")
        print("=======================\n")
        
    except subprocess.TimeoutExpired:
        pytest.fail(f"Model generation timed out after 30 seconds for {test_model}")
    except subprocess.CalledProcessError as e:
        pytest.fail(f"CLI command failed with error: {e.stderr}")
    except Exception as e:
        pytest.fail(f"Unexpected error during test: {str(e)}") 