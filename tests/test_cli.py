"""
Tests for the CLI module.

These tests verify that the command-line interface functions correctly with llama.cpp.
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
import argparse
import sys

from orac.cli import (
    setup_client, check_status, list_models, 
    generate_text, test_model, main
)


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


# Tests for the CLI functions
@pytest.mark.asyncio
async def test_setup_client():
    """Test setting up the client."""
    with patch("orac.cli.LlamaCppClient") as mock_client_class:
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        
        # Call the function
        client = await setup_client()
        
        # Check results
        assert client == mock_client
        mock_client_class.assert_called_once()
        
        # Call again to test singleton behavior
        client2 = await setup_client()
        assert client2 == client
        assert mock_client_class.call_count == 1


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