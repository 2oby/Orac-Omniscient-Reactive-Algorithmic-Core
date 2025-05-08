"""Configure pytest for the test suite."""

import pytest

# Configure pytest-asyncio
pytest_plugins = ("pytest_asyncio",)

def pytest_configure(config):
    config.addinivalue_line(
        "asyncio_mode",
        "auto"
    )
    config.addinivalue_line(
        "asyncio_default_fixture_loop_scope",
        "function"
    )

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