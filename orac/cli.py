"""
orac.cli
--------
Command-line interface for ORAC that provides functionality for:
- Loading and testing models
- Generating text from models
- Checking system status
- Managing models (list, load, unload)

This module serves as both a testing tool and a convenient way to interact with
the Ollama service without using the API directly.
"""

import os
import sys
import time
import json
import argparse
import asyncio
from typing import Dict, Any, List

from orac.logger import get_logger
from orac.ollama_client import OllamaClient
from orac.models import GenerationRequest

# Configure logger
logger = get_logger(__name__)

# Global client instance
client = None


async def setup_client() -> OllamaClient:
    """Set up and return the Ollama client."""
    global client
    if client is None:
        # Get Ollama host and port from environment variables
        ollama_host = os.environ.get("OLLAMA_HOST", "127.0.0.1")
        ollama_port = os.environ.get("OLLAMA_PORT", "11434")
        base_url = f"http://{ollama_host}:{ollama_port}"
        
        logger.info(f"Connecting to Ollama at {base_url}")
        client = OllamaClient(base_url)
    
    return client


async def close_client():
    """Close the Ollama client."""
    global client
    if client:
        await client.close()
        client = None


async def check_ollama_status() -> bool:
    """Check if Ollama is running and responsive."""
    client = await setup_client()
    try:
        version = await client.get_version()
        if version == "unknown":
            logger.error("Ollama is not responding")
            return False
        
        logger.info(f"Ollama is running (version: {version})")
        return True
    except Exception as e:
        logger.error(f"Error checking Ollama status: {str(e)}")
        return False


async def list_models() -> List[Dict[str, Any]]:
    """List all available models."""
    client = await setup_client()
    try:
        models = await client.list_models()
        
        # Print models in a readable format
        if not models:
            logger.info("No models available")
            print("No models available")
        else:
            logger.info(f"Found {len(models)} models")
            print(f"Available models ({len(models)}):")
            for i, model in enumerate(models, 1):
                name = model.get("name", "unknown")
                size_bytes = model.get("size", 0)
                size_mb = size_bytes / (1024 * 1024) if size_bytes else 0
                modified = model.get("modified_at", "unknown")
                
                print(f"{i}. {name} ({size_mb:.2f} MB, modified: {modified})")
        
        return models
    except Exception as e:
        logger.error(f"Error listing models: {str(e)}")
        print(f"Error: {str(e)}")
        return []


async def load_model(name: str) -> Dict[str, Any]:
    """Load a model by name."""
    client = await setup_client()
    
    print(f"Loading model: {name}...")
    logger.info(f"Loading model: {name}")
    
    try:
        start_time = time.time()
        result = await client.load_model(name)
        elapsed = time.time() - start_time
        
        if result.get("status") == "success":
            print(f"✓ Model '{name}' loaded successfully in {elapsed:.2f} seconds")
            logger.info(f"Model '{name}' loaded successfully in {elapsed:.2f} seconds")
        else:
            error_msg = result.get("message", "Unknown error")
            print(f"✗ Failed to load model: {error_msg}")
            logger.error(f"Failed to load model: {error_msg}")
        
        return result
    except Exception as e:
        logger.exception(f"Error loading model: {str(e)}")
        print(f"✗ Error: {str(e)}")
        return {"status": "error", "message": str(e)}


async def unload_model(name: str) -> Dict[str, Any]:
    """Unload a model by name."""
    client = await setup_client()
    
    print(f"Unloading model: {name}...")
    logger.info(f"Unloading model: {name}")
    
    try:
        result = await client.unload_model(name)
        
        if result.get("status") == "success":
            print(f"✓ Model '{name}' unloaded successfully")
            logger.info(f"Model '{name}' unloaded successfully")
        else:
            error_msg = result.get("message", "Unknown error")
            print(f"✗ Failed to unload model: {error_msg}")
            logger.error(f"Failed to unload model: {error_msg}")
        
        return result
    except Exception as e:
        logger.exception(f"Error unloading model: {str(e)}")
        print(f"✗ Error: {str(e)}")
        return {"status": "error", "message": str(e)}


async def generate_text(model: str, prompt: str, stream: bool = False) -> Dict[str, Any]:
    """Generate text from a model."""
    client = await setup_client()
    
    # First check if the model is loaded
    logger.info(f"Checking if model '{model}' is loaded")
    try:
        models = await client.list_models()
        model_names = [m.get("name", "") for m in models]
        
        if model not in model_names:
            logger.warning(f"Model '{model}' not loaded, attempting to load it now")
            print(f"Model '{model}' not loaded, loading it now...")
            load_result = await client.load_model(model)
            
            if load_result.get("status") != "success":
                error_msg = load_result.get("message", "Unknown error")
                print(f"✗ Failed to load model: {error_msg}")
                logger.error(f"Failed to load model: {error_msg}")
                return {"status": "error", "message": f"Failed to load model: {error_msg}"}
    except Exception as e:
        logger.error(f"Error checking model status: {str(e)}")
    
    print(f"Generating text with model '{model}'...")
    if stream:
        print("Streaming response:")
    
    logger.info(f"Generating text with model '{model}', prompt: '{prompt[:50]}...'")
    
    try:
        start_time = time.time()
        result = await client.generate(model, prompt, stream=stream)
        elapsed = time.time() - start_time
        
        if result.get("status") == "success":
            response_text = result.get("response", "")
            elapsed_ms = result.get("elapsed_ms", 0)
            
            if not stream:
                print("\nGenerated text:")
                print("-------------------")
                print(response_text)
                print("-------------------")
            
            print(f"\n✓ Generation completed in {elapsed_ms/1000:.2f} seconds")
            logger.info(f"Generation completed in {elapsed_ms/1000:.2f} seconds, response length: {len(response_text)} chars")
        else:
            error_msg = result.get("message", "Unknown error")
            print(f"✗ Failed to generate text: {error_msg}")
            logger.error(f"Failed to generate text: {error_msg}")
        
        return result
    except Exception as e:
        logger.exception(f"Error generating text: {str(e)}")
        print(f"✗ Error: {str(e)}")
        return {"status": "error", "message": str(e)}


async def test_model(model: str) -> Dict[str, Any]:
    """Test a model with a simple prompt."""
    print(f"Testing model '{model}' with a simple prompt...")
    logger.info(f"Testing model '{model}' with a simple prompt")
    
    # Simple test prompt
    test_prompt = "Write a haiku about artificial intelligence."
    
    result = await generate_text(model, test_prompt)
    return result


async def pull_model(name: str) -> Dict[str, Any]:
    """Pull a model from Ollama library."""
    client = await setup_client()
    
    print(f"Pulling model: {name}...")
    logger.info(f"Pulling model: {name}")
    
    try:
        start_time = time.time()
        result = await client.pull_model(name)
        elapsed = time.time() - start_time
        
        if result.get("status") == "success":
            print(f"✓ Model '{name}' pulled successfully in {elapsed:.2f} seconds")
            logger.info(f"Model '{name}' pulled successfully in {elapsed:.2f} seconds")
        else:
            error_msg = result.get("message", "Unknown error")
            print(f"✗ Failed to pull model: {error_msg}")
            logger.error(f"Failed to pull model: {error_msg}")
        
        return result
    except Exception as e:
        logger.exception(f"Error pulling model: {str(e)}")
        print(f"✗ Error: {str(e)}")
        return {"status": "error", "message": str(e)}


async def show_model(name: str) -> Dict[str, Any]:
    """Show details about a model."""
    client = await setup_client()
    
    print(f"Getting details for model: {name}...")
    logger.info(f"Getting details for model: {name}")
    
    try:
        result = await client.show_model(name)
        
        if result.get("status") == "success":
            model_info = result.get("model", {})
            print(f"Model '{name}' details:")
            print(json.dumps(model_info, indent=2))
            logger.info(f"Retrieved details for model '{name}'")
        else:
            error_msg = result.get("message", "Unknown error")
            print(f"✗ Failed to get model details: {error_msg}")
            logger.error(f"Failed to get model details: {error_msg}")
        
        return result
    except Exception as e:
        logger.exception(f"Error getting model details: {str(e)}")
        print(f"✗ Error: {str(e)}")
        return {"status": "error", "message": str(e)}


async def run_command(args):
    """Run the specified command with arguments."""
    if args.command == "status":
        await check_ollama_status()
    
    elif args.command == "list":
        await list_models()
    
    elif args.command == "load":
        if not args.model:
            print("Error: Model name is required for load command")
            return
        await load_model(args.model)
    
    elif args.command == "unload":
        if not args.model:
            print("Error: Model name is required for unload command")
            return
        await unload_model(args.model)
    
    elif args.command == "generate":
        if not args.model or not args.prompt:
            print("Error: Model name and prompt are required for generate command")
            return
        await generate_text(args.model, args.prompt, stream=args.stream)
    
    elif args.command == "test":
        if not args.model:
            print("Error: Model name is required for test command")
            return
        await test_model(args.model)
    
    elif args.command == "pull":
        if not args.model:
            print("Error: Model name is required for pull command")
            return
        await pull_model(args.model)
    
    elif args.command == "show":
        if not args.model:
            print("Error: Model name is required for show command")
            return
        await show_model(args.model)
    
    else:
        print(f"Unknown command: {args.command}")


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="ORAC CLI - Interact with Ollama models")
    subparsers = parser.add_subparsers(dest="command", help="Command to run")
    
    # Status command
    status_parser = subparsers.add_parser("status", help="Check Ollama status")
    
    # List command
    list_parser = subparsers.add_parser("list", help="List available models")
    
    # Load command
    load_parser = subparsers.add_parser("load", help="Load a model")
    load_parser.add_argument("model", help="Model name to load")
    
    # Unload command
    unload_parser = subparsers.add_parser("unload", help="Unload a model")
    unload_parser.add_argument("model", help="Model name to unload")
    
    # Generate command
    generate_parser = subparsers.add_parser("generate", help="Generate text from a model")
    generate_parser.add_argument("model", help="Model to use")
    generate_parser.add_argument("prompt", help="Prompt text")
    generate_parser.add_argument("--stream", action="store_true", help="Stream the response")
    
    # Test command
    test_parser = subparsers.add_parser("test", help="Test a model with a simple prompt")
    test_parser.add_argument("model", help="Model to test")
    
    # Pull command
    pull_parser = subparsers.add_parser("pull", help="Pull a model from Ollama library")
    pull_parser.add_argument("model", help="Model name to pull")
    
    # Show command
    show_parser = subparsers.add_parser("show", help="Show details about a model")
    show_parser.add_argument("model", help="Model name to show")
    
    return parser.parse_args()


async def main():
    """Main entry point for the CLI."""
    try:
        args = parse_args()
        
        # If no command is specified, print help
        if not args.command:
            print("Error: Command is required")
            print("Available commands: status, list, load, unload, generate, test, pull, show")
            return 1
        
        await run_command(args)
        return 0
    except KeyboardInterrupt:
        print("\nOperation canceled by user")
        return 130
    except Exception as e:
        logger.exception(f"Unhandled exception: {str(e)}")
        print(f"Error: {str(e)}")
        return 1
    finally:
        await close_client()


if __name__ == "__main__":
    # Run the async main function
    exit_code = asyncio.run(main())
    sys.exit(exit_code)