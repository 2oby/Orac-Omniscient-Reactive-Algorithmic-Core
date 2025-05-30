"""
orac.cli
--------
Command-line interface for ORAC that provides functionality for:
- Loading and testing models
- Generating text from models
- Checking system status
- Managing models (list, load, unload)

This module serves as both a testing tool and a convenient way to interact with
llama.cpp directly.
"""

import os
import sys
import time
import json
import argparse
import asyncio
from typing import Dict, Any, List

from orac.logger import get_logger
from orac.llama_cpp_client import LlamaCppClient
from orac.models import GenerationRequest

# Configure logger
logger = get_logger(__name__)

# Global client instance
client = None

async def setup_client() -> LlamaCppClient:
    """Set up and return the llama.cpp client."""
    global client
    if client is None:
        logger.info("Initializing llama.cpp client")
        client = LlamaCppClient()
    return client

async def close_client():
    """Close the llama.cpp client."""
    global client
    if client:
        client = None

async def check_status() -> bool:
    """Check if llama.cpp is working correctly."""
    client = await setup_client()
    try:
        # Try to list models as a basic health check
        models = await client.list_models()
        logger.info(f"Found {len(models)} models")
        return True
    except Exception as e:
        logger.error(f"Error checking llama.cpp status: {str(e)}")
        return False

async def list_models() -> List[Dict[str, Any]]:
    """List available models."""
    client = await setup_client()
    try:
        return await client.list_models()
    except Exception as e:
        logger.error(f"Error listing models: {str(e)}")
        return []

async def load_model(model_name: str) -> Dict[str, Any]:
    """Load a model."""
    client = await setup_client()
    try:
        return await client.load_model(model_name)
    except Exception as e:
        logger.error(f"Error loading model: {str(e)}")
        return {"status": "error", "message": str(e)}

async def unload_model(model_name: str) -> Dict[str, Any]:
    """Unload a model."""
    client = await setup_client()
    try:
        return await client.unload_model(model_name)
    except Exception as e:
        logger.error(f"Error unloading model: {str(e)}")
        return {"status": "error", "message": str(e)}

async def generate_text(model_name: str, prompt: str, stream: bool = False, verbose: bool = False) -> Dict[str, Any]:
    """Generate text from a model."""
    client = await setup_client()
    try:
        response = await client.generate(
            model=model_name,
            prompt=prompt,
            stream=stream,
            temperature=0.7,
            top_p=0.7,
            top_k=40,
            max_tokens=512,
            verbose=verbose,
            timeout=30
        )
        return {
            "status": "success",
            "response": response.response,
            "elapsed_ms": response.elapsed_ms
        }
    except Exception as e:
        logger.error(f"Error generating text: {str(e)}")
        return {"status": "error", "message": str(e)}

async def test_model(model_name: str) -> Dict[str, Any]:
    """Test a model with a simple prompt."""
    try:
        # Generate test text
        test_prompt = "Write a haiku about AI running on a Jetson Orin"
        gen_result = await generate_text(model_name, test_prompt)
        if gen_result["status"] != "success":
            return gen_result
        
        return {
            "status": "success",
            "generation_time": gen_result.get("elapsed_ms", 0) / 1000,
            "response": gen_result["response"]
        }
    except Exception as e:
        logger.error(f"Error testing model: {str(e)}")
        return {"status": "error", "message": str(e)}

async def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(description="ORAC CLI")
    parser.add_argument("command", choices=["status", "list", "load", "unload", "generate", "test"], help="Command to execute")
    parser.add_argument("--model", help="Model name for generation")
    parser.add_argument("--prompt", help="Prompt for generation")
    parser.add_argument("--stream", action="store_true", help="Stream the generation output")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose output for generation")
    args = parser.parse_args()

    try:
        if args.command == "status":
            if await check_status():
                print("llama.cpp is running correctly")
                sys.exit(0)
            else:
                print("llama.cpp is not working correctly")
                sys.exit(1)
        
        elif args.command == "list":
            models = await list_models()
            print("\nAvailable models:")
            for model in models:
                print(f"- {model['name']} ({model['size'] / (1024*1024):.1f} MB)")
        
        elif args.command == "load":
            if not args.model:
                print("Error: --model is required for loading")
                sys.exit(1)
            result = await load_model(args.model)
            print(json.dumps(result, indent=2))
        
        elif args.command == "unload":
            if not args.model:
                print("Error: --model is required for unloading")
                sys.exit(1)
            result = await unload_model(args.model)
            print(json.dumps(result, indent=2))
        
        elif args.command == "generate":
            if not args.model or not args.prompt:
                print("Error: --model and --prompt are required for generation")
                sys.exit(1)
            result = await generate_text(args.model, args.prompt, args.stream, verbose=args.verbose)
            if result["status"] == "success":
                print("\nGenerated response:")
                print(result["response"])
            else:
                print(f"Error: {result['message']}")
                sys.exit(1)
        
        elif args.command == "test":
            if not args.model:
                print("Error: --model is required for testing")
                sys.exit(1)
            result = await test_model(args.model)
            print(json.dumps(result, indent=2))
    
    except Exception as e:
        logger.error(f"Error executing command: {str(e)}")
        sys.exit(1)
    finally:
        await close_client()

if __name__ == "__main__":
    asyncio.run(main())