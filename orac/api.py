# orac/api.py
from fastapi import FastAPI, HTTPException
from orac import ollama_client as oc
from orac.models import ModelListResponse, ModelInfo


app = FastAPI(title="ORAC API", version="0.1.0‑mvp")


@app.get("/v1/models", response_model=ModelListResponse)
async def list_models():
    try:
        raw_models = await oc.list_models()
        parsed = [ModelInfo(**m) for m in raw_models]
        return {"models": parsed}
    except Exception as exc:   # catch httpx errors etc.
        raise HTTPException(status_code=502, detail=str(exc)) from exc
