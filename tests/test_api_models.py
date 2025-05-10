import pytest
from fastapi.testclient import TestClient
import respx
from httpx import Response
import os
from pathlib import Path
from unittest.mock import patch

from orac.api import app

client = TestClient(app)


@respx.mock
def test_list_models_endpoint():
    # Mock the local model directory
    test_models_dir = Path("/app/models")
    test_models = [
        {"name": "tinyllama", "size": 1000000, "modified": 1234567890.0}
    ]
    
    with patch("pathlib.Path.glob") as mock_glob:
        mock_glob.return_value = [
            test_models_dir / "tinyllama.gguf"
        ]
        with patch("pathlib.Path.stat") as mock_stat:
            mock_stat.return_value.st_size = 1000000
            mock_stat.return_value.st_mtime = 1234567890.0
            
            resp = client.get("/v1/models")
            assert resp.status_code == 200
            assert resp.json() == {
                "models": [
                    {
                        "name": "tinyllama",
                        "size": 1000000,
                        "modified": 1234567890.0,
                        "backend": "llama_cpp"
                    }
                ]
            }
