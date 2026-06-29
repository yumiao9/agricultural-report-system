"""Pytest fixtures for the agricultural report system."""

import pytest
from starlette.testclient import TestClient


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    from backend.main import app
    return TestClient(app, raise_server_exceptions=False)
