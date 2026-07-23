"""Pytest configuration and global fixtures for forecast_fusion tests."""

import sys
from unittest.mock import MagicMock

# Mock fcntl module on Windows for Home Assistant runner compatibility
if sys.platform == "win32" and "fcntl" not in sys.modules:
    sys.modules["fcntl"] = MagicMock()

import pytest
import pytest_socket

# Disable pytest_socket blocking on Windows for asyncio event loop self-pipe setup
pytest_socket.disable_socket = lambda *args, **kwargs: None

pytest_plugins = ["pytest_homeassistant_custom_component"]


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations in Home Assistant pytest environment."""
    yield
