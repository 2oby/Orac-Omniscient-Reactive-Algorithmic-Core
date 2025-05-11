import pytest
from fastapi.testclient import TestClient
from orac.api.main import app

@pytest.fixture
def client():
    """Create a test client for the API."""
    return TestClient(app)

def test_health_check(client):
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "orac" 