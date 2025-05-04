"""Configure pytest for the test suite."""

import pytest

# Configure pytest-asyncio to use function scope for event loops
def pytest_configure(config):
    config.option.asyncio_default_fixture_loop_scope = "function" 