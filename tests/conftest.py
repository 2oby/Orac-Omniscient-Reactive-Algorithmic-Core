"""
Test configuration and fixtures for ORAC tests.
"""

import pytest
import logging
import os
import shutil
from typing import Generator, Dict, Any
import httpx
from pathlib import Path
from orac.model_loader import ModelLoader
from orac.llama_cpp_client import LlamaCppClient

# Test log directory - use absolute path in project root
TEST_LOG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "test_logs")

@pytest.fixture(scope="session", autouse=True)
def setup_test_logging():
    """Set up test logging directory."""
    # Set test log directory
    os.environ["ORAC_LOG_DIR"] = TEST_LOG_DIR
    
    # Create test log directory
    log_dir = Path(TEST_LOG_DIR)
    if log_dir.exists():
        shutil.rmtree(log_dir)
    log_dir.mkdir(parents=True)
    
    yield
    
    # Clean up test logs after all tests
    if log_dir.exists():
        shutil.rmtree(log_dir)

@pytest.fixture
def llama_cpp_client() -> Generator[LlamaCppClient, None, None]:
    """Create a LlamaCppClient instance for testing."""
    with httpx.Client(base_url="http://localhost:8000") as client:
        yield LlamaCppClient(client)

@pytest.fixture
def model_loader(llama_cpp_client: LlamaCppClient) -> Generator[ModelLoader, None, None]:
    """Create a ModelLoader instance for testing."""
    yield ModelLoader(llama_cpp_client.client)

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
        
        # Print logs from file for failed tests
        log_file = Path(TEST_LOG_DIR) / "model_loader.log"
        if log_file.exists():
            print("\n=== Model Loader Logs ===")
            with open(log_file) as f:
                print(f.read())

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