"""Global pytest configuration."""
import pytest

# Configure pytest-asyncio
pytest_plugins = ["pytest_asyncio"]

def pytest_configure(config):
    """Configure pytest."""
    config.option.asyncio_mode = "strict"
    config.option.asyncio_default_fixture_loop_scope = "function" 