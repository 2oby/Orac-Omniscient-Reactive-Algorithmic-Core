# orac/models.py
from typing import List

from pydantic import BaseModel


class ModelInfo(BaseModel):
    name: str
    modified: str | None = None   # ISO 8601 timestamp from Ollama
    size: int | None = None       # bytes; Ollama omits this sometimes


class ModelListResponse(BaseModel):
    models: List[ModelInfo]
