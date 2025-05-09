"""
Tests for the CLI module.

These tests verify that the command-line interface functions correctly.
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
import argparse
import sys

from orac.cli import (
    setup_client, check_ollama_status, list_models, 
    load_model, unload_model, generate_text, test_model,
    run_command, parse_args
)


# Fixtures
@pytest.fixture
def mock_ollama_client():
    """Create a mock OllamaClient for testing."""
    client = AsyncMock()
    client.get_version.return_value = "0.6.0"
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
    with patch("orac.cli.OllamaClient") as mock_client_class:
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
async def test_check_ollama_status(mock_ollama_client):
    """Test checking Ollama status."""
    with patch("orac.cli.setup_client", return_value=mock_ollama_client):
        # Test with Ollama running
        mock_ollama_client.get_version.return_value = "0.6.0"
        status = await check_ollama_status()
        assert status is True
        
        # Test with Ollama not running
        mock_ollama_client.get_version.return_value = "unknown"
        status = await check_ollama_status()
        assert status is False
        
        # Test with exception
        mock_ollama_client.get_version.side_effect = Exception("Connection error")
        status = await check_ollama_status()
        assert status is False


@pytest.mark.asyncio
async def test_list_models(mock_ollama_client):
    """Test listing models."""
    with patch("orac.cli.setup_client", return_value=mock_ollama_client):
        # Test with models available
        models = await list_models()
        assert len(models) == 2
        assert models[0]["name"] == "model1"
        
        # Test with no models
        mock_ollama_client.list_models.return_value = []
        models = await list_models()
        assert len(models) == 0
        
        # Test with exception
        mock_ollama_client.list_models.side_effect = Exception("Connection error")
        models = await list_models()
        assert models == []


@pytest.mark.asyncio
async def test_load_model(mock_ollama_client):
    """Test loading a model."""
    with patch("orac.cli.setup_client", return_value=mock_ollama_client):
        # Test successful load
        mock_ollama_client.load_model.return_value = {
            "status": "success",
            "elapsed_seconds": 10.5
        }
        result = await load_model("test-model")
        assert result["status"] == "success"
        mock_ollama_client.load_model.assert_called_once_with("test-model")
        
        # Test failed load
        mock_ollama_client.load_model.return_value = {
            "status": "error",
            "message": "Model file not found"
        }
        result = await load_model("test-model")
        assert result["status"] == "error"
        
        # Test with exception
        mock_ollama_client.load_model.side_effect = Exception("Connection error")
        result = await load_model("test-model")
        assert result["status"] == "error"
        assert "Connection error" in result["message"]


@pytest.mark.asyncio
async def test_unload_model(mock_ollama_client):
    """Test unloading a model."""
    with patch("orac.cli.setup_client", return_value=mock_ollama_client):
        # Test successful unload
        mock_ollama_client.unload_model.return_value = {"status": "success"}
        result = await unload_model("test-model")
        assert result["status"] == "success"
        mock_ollama_client.unload_model.assert_called_once_with("test-model")
        
        # Test failed unload
        mock_ollama_client.unload_model.return_value = {
            "status": "error",
            "message": "Model not found"
        }
        result = await unload_model("test-model")
        assert result["status"] == "error"
        
        # Test with exception
        mock_ollama_client.un