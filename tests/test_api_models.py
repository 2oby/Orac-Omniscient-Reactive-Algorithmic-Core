import pytest
from fastapi.testclient import TestClient
import respx
from httpx import Response

from orac.api import app

client = TestClient(app)


@respx.mock
def test_list_models_endpoint():
    respx.get("http://127.0.0.1:11434/api/tags").mock(
        return_value=Response(200, json={"models": [{"name": "tinyllama"}]})
    )
    resp = client.get("/v1/models")
    assert resp.status_code == 200
    assert resp.json() == {"models": [{"name": "tinyllama", "modified": None, "size": None}]}
