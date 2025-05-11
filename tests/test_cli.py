"""
Tests for the CLI module.

These tests verify that the command-line interface functions correctly with llama.cpp.
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
import argparse
import sys
from typing import Dict, Any
import logging

from orac.cli import (
    setup_client, check_status, list_models, 
    generate_text, test_model, main, close_client
)

logger = logging.getLogger(__name__)

# Fixtures
@pytest.fixture
def mock_llama_client():
    """Create a mock LlamaCppClient for testing."""
    client = AsyncMock()
    client.list_models.return_value = [
        {"name": "model1", "size": 1000000},
        {"name": "model2", "size": 2000000}
    ]
    return client


@pytest.fixture
def mock_args():
    """Create mock command-line arguments."""
    args = argparse.Namespace()
    args.command = "status"
    args.model = None
    args.prompt = None
    args.stream = False
    return args


@pytest.fixture
def model_name():
    """Return the name of the model to test with."""
    return "Qwen3-0.6B-Q4_K_M.gguf"


# Tests for the CLI functions
@pytest.mark.asyncio
async def test_setup_client():
    """Test setting up the client."""
    # Create a mock client
    mock_client = AsyncMock()
    
    # Mock the LlamaCppClient class to return our mock client
    with patch("orac.cli.LlamaCppClient", return_value=mock_client) as mock_client_class:
        # First call should create a new client
        client = await setup_client()
        assert client == mock_client
        mock_client_class.assert_called_once()
        
        # Reset the mock to verify it's not called again
        mock_client_class.reset_mock()
        
        # Second call should return the same client (singleton pattern)
        client2 = await setup_client()
        assert client2 == client
        assert mock_client_class.call_count == 0  # Should not create a new instance
        
        # Clear the global client to test singleton reset
        await close_client()
        
        # Next call should create a new client again
        client3 = await setup_client()
        assert client3 == mock_client
        mock_client_class.assert_called_once()


@pytest.mark.asyncio
async def test_check_status(mock_llama_client):
    """Test checking llama.cpp status."""
    with patch("orac.cli.setup_client", return_value=mock_llama_client):
        # Test with models available
        status = await check_status()
        assert status is True
        
        # Test with no models
        mock_llama_client.list_models.return_value = []
        status = await check_status()
        assert status is True  # Still true because we can list models
        
        # Test with exception
        mock_llama_client.list_models.side_effect = Exception("Connection error")
        status = await check_status()
        assert status is False


@pytest.mark.asyncio
async def test_list_models(mock_llama_client):
    """Test listing models."""
    with patch("orac.cli.setup_client", return_value=mock_llama_client):
        # Test with models available
        models = await list_models()
        assert len(models) == 2
        assert models[0]["name"] == "model1"
        
        # Test with no models
        mock_llama_client.list_models.return_value = []
        models = await list_models()
        assert len(models) == 0
        
        # Test with exception
        mock_llama_client.list_models.side_effect = Exception("Connection error")
        models = await list_models()
        assert models == []


@pytest.mark.asyncio
async def test_main_status_command(mock_llama_client):
    """Test the main function with status command."""
    with patch("orac.cli.setup_client", return_value=mock_llama_client), \
         patch("sys.argv", ["orac", "status"]), \
         patch("sys.exit") as mock_exit:
        
        # Test successful status
        await main()
        mock_exit.assert_called_once_with(0)
        
        # Test failed status
        mock_llama_client.list_models.side_effect = Exception("Connection error")
        await main()
        mock_exit.assert_called_with(1)


@pytest.mark.asyncio
async def test_main_list_command(mock_llama_client):
    """Test the main function with list command."""
    with patch("orac.cli.setup_client", return_value=mock_llama_client), \
         patch("sys.argv", ["orac", "list"]), \
         patch("builtins.print") as mock_print:
        
        await main()
        mock_print.assert_called()


@pytest.mark.asyncio
async def test_main_generate_command(mock_llama_client):
    """Test the main function with generate command."""
    with patch("orac.cli.setup_client", return_value=mock_llama_client), \
         patch("sys.argv", ["orac", "generate", "--model", "test-model", "--prompt", "test prompt"]), \
         patch("builtins.print") as mock_print:
        
        mock_llama_client.generate.return_value = MagicMock(
            response="test response",
            elapsed_ms=100
        )
        await main()
        mock_print.assert_called()


@pytest.mark.asyncio
async def test_model(model_name: str) -> Dict[str, Any]:
    """Test a model with a simple prompt."""
    try:
        # Generate test text
        test_prompt = "Write a haiku about AI running on a Jetson Orin"
        logger.info(f"Testing model {model_name} with prompt: {test_prompt}")
        
        gen_result = await generate_text(model_name, test_prompt)
        if gen_result["status"] != "success":
            logger.error(f"Generation failed: {gen_result}")
            return gen_result
        
        response = gen_result["response"]
        generation_time = gen_result.get("elapsed_ms", 0) / 1000
        
        logger.info(f"Model response ({generation_time:.2f}s):\n{response}")
        
        return {
            "status": "success",
            "generation_time": generation_time,
            "response": response
        }
    except Exception as e:
        logger.error(f"Error testing model: {str(e)}")
        return {"status": "error", "message": str(e)}