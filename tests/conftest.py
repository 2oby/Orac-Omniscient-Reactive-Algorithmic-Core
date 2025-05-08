"""Configure pytest for the test suite."""

import pytest
import logging
import os
from typing import Generator, Dict, Any
import httpx
from orac.ollama_client import OllamaClient
from orac.model_loader import ModelLoader

@pytest.fixture
def ollama_client() -> Generator[OllamaClient, None, None]:
    """Create an OllamaClient instance for testing."""
    with httpx.Client(base_url="http://localhost:11434") as client:
        yield OllamaClient(client)

@pytest.fixture
def model_loader(ollama_client: OllamaClient) -> Generator[ModelLoader, None, None]:
    """Create a ModelLoader instance for testing."""
    yield ModelLoader(ollama_client.client)

@pytest.fixture(autouse=True)
def capture_logs(request):
    """Capture logs during test execution."""
    # Create a handler that captures log records
    records = []
    handler = logging.Handler()
    handler.emit = lambda record: records.append(record)
    
    # Add handler to root logger
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    
    yield
    
    # Remove handler
    root_logger.removeHandler(handler)
    
    # Store logs in test report if test failed
    if hasattr(request.node, 'rep_call') and request.node.rep_call.failed:
        request.node.rep_call.logs = records

def pytest_exception_interact(call, report):
    """Disable traceback in test output."""
    if report.failed:
        # Only show the error message, not the traceback
        report.longrepr = str(call.excinfo.value)

@pytest.fixture(autouse=True)
def capture_logs(request):
    """Fixture to capture and format logs for failed tests."""
    yield
    # Only try to capture logs if the test failed
    if hasattr(request.node, 'rep_call') and request.node.rep_call.failed:
        # Get the client from the test function
        client = request.function.__globals__.get('client')
        if client and hasattr(client, 'model_loader'):
            debug_logs = client.model_loader.get_debug_logs()
            error_logs = client.model_loader.get_error_logs()
            
            if debug_logs or error_logs:
                print("\n=== Debug Logs ===")
                for log in debug_logs:
                    print(f"{log['stage']}: {log.get('data', {})}")
                
                print("\n=== Error Logs ===")
                for log in error_logs:
                    print(log) 