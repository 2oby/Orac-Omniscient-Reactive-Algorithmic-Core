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

async def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(description="ORAC CLI")
    parser.add_argument("command", choices=["status", "list", "generate"], help="Command to execute")
    parser.add_argument("--model", help="Model name for generation")
    parser.add_argument("--prompt", help="Prompt for generation")
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
            client = await setup_client()
            models = await client.list_models()
            print("\nAvailable models:")
            for model in models:
                print(f"- {model['name']} ({model['size'] / (1024*1024):.1f} MB)")
        
        elif args.command == "generate":
            if not args.model or not args.prompt:
                print("Error: --model and --prompt are required for generation")
                sys.exit(1)
            
            client = await setup_client()
            response = await client.generate(args.model, args.prompt)
            print("\nGenerated response:")
            print(response.response)
    
    except Exception as e:
        logger.error(f"Error executing command: {str(e)}")
        sys.exit(1)
    finally:
        await close_client()

if __name__ == "__main__":
    asyncio.run(main())