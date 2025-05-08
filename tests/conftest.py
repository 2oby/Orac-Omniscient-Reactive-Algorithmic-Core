"""Configure pytest for the test suite."""

import pytest
import logging
import os
from typing import Generator, Dict, Any
import asyncio

# Configure pytest-asyncio
pytest_plugins = ("pytest_asyncio",)

def pytest_configure(config):
    """Configure pytest with asyncio settings."""
    # Set asyncio mode and fixture loop scope
    config.option.asyncio_mode = "auto"
    config.option.asyncio_default_fixture_loop_scope = "function"
    
    # Add markers
    config.addinivalue_line(
        "markers",
        "asyncio: mark test as async"
    )

@pytest.fixture(scope="function")
async def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()

@pytest.fixture(autouse=True)
def setup_logging():
    """Set up logging for all tests."""
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

@pytest.fixture
def capture_logs(request) -> Generator[Dict[str, Any], None, None]:
    """Capture logs during test execution."""
    logs = {"debug": [], "error": []}
    
    class LogCapture:
        def __init__(self, logs):
            self.logs = logs
            
        def debug(self, msg, *args, **kwargs):
            self.logs["debug"].append(msg)
            
        def error(self, msg, *args, **kwargs):
            self.logs["error"].append(msg)
    
    capture = LogCapture(logs)
    yield logs
    
    # Log test results if test failed
    if hasattr(request.node, 'rep_call') and request.node.rep_call.failed:
        logging.error("Test failed. Captured logs:")
        for level, messages in logs.items():
            for msg in messages:
                logging.error(f"{level.upper()}: {msg}")

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