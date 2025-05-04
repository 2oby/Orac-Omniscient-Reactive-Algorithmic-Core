import pytest
import respx
from httpx import Response
import orac.ollama_client as oc


@respx.mock
@pytest.mark.asyncio
async def test_list_models_parses_result():
    fake = respx.get("http://127.0.0.1:11434/api/tags").mock(
        return_value=Response(200, json={"models": [{"name": "tiny"}]})
    )
    models = await oc.list_models()
    assert fake.called
    assert models == [{"name": "tiny"}]

