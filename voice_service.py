#!/usr/bin/env python3
"""
Voice Service – Smart‑Home Control
Fully self‑contained version (no placeholders trimmed) – ready for docker run.
"""

# ---------------------------------------------------------------------------
# Standard library imports
# ---------------------------------------------------------------------------
import os
import sys
import time
import gc
import json
import traceback
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
import asyncio

# ---------------------------------------------------------------------------
# Third‑party imports
# ---------------------------------------------------------------------------
import psutil
import torch
import uvicorn
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
from pydantic import BaseModel, Field
from transformers import AutoModelForCausalLM, AutoTokenizer
import pkg_resources
from asyncio import Lock

# ---------------------------------------------------------------------------
# Project‑local imports (must be available in PYTHONPATH / same image)
# ---------------------------------------------------------------------------
from response_to_JSON_integration import (
    generate_json_from_response,  # noqa
    create_prompt,
    SmartHomeCommand,  # noqa – retained for external callers
    process_command,
)

# ---------------------------------------------------------------------------
# Logging & device setup
# ---------------------------------------------------------------------------
start_time = time.time()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("/app/logs/voice_service.log")],
)
logger = logging.getLogger("voice-service")

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
logger.info(f"Using device: {DEVICE}")
if DEVICE == "cuda":
    try:
        props = torch.cuda.get_device_properties(0)
        logger.info(f"GPU: {props.name} | {props.total_memory/1e9:.2f} GB")
    except Exception as gpu_err:
        logger.warning(f"GPU introspection failed: {gpu_err}")

# ---------------------------------------------------------------------------
# Directories
# ---------------------------------------------------------------------------
MODELS_DIR = os.environ.get("MODELS_DIR", "/models")
CONFIG_DIR = os.environ.get("CONFIG_DIR", "/app/config")
os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(CONFIG_DIR, exist_ok=True)
logger.info(f"Models directory: {MODELS_DIR}")
logger.info(f"Config directory: {CONFIG_DIR}")

# ---------------------------------------------------------------------------
# Model aliases & recommendations
# ---------------------------------------------------------------------------
MODEL_ALIASES: dict[str, str] = {
    "tinyllama": "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
    "pythia": "EleutherAI/pythia-70m",
    "phi2": "microsoft/phi-2",
    "mistral": "nilq/mistral-1L-tiny",
    "qwen": "Qwen/Qwen1.5-0.5B-Chat",
    "qwen3-1.7b": "Qwen/Qwen3-1.7B",
    "qwen3-0.6b": "Qwen/Qwen3-0.6B",
    "qwen3-0.6b-fp8": "Qwen/Qwen3-0.6B-FP8",
}

RECOMMENDED_MODELS: list[str] = [
    "tinyllama",
    "qwen3-0.6b",
    "qwen3-0.6b-fp8",
    "qwen3-1.7b",
    "distilgpt2",
    "gpt2",
]

# ---------------------------------------------------------------------------
# In‑memory state
# ---------------------------------------------------------------------------
loaded_models: dict[str, Dict[str, Any]] = {}
current_model_id: Optional[str] = None
model_lock = Lock()

# ---------------------------------------------------------------------------
# Helper functions – filesystem ↔ HF model id
# ---------------------------------------------------------------------------

def model_id_to_dir_name(model_id: str) -> str:
    return "models--" + "--".join(model_id.split("/"))


def dir_name_to_model_id(dir_name: str) -> str:
    if not dir_name.startswith("models--"):
        return dir_name
    return "/".join(dir_name[len("models--") :].split("--"))


def list_available_models() -> List[str]:
    cache = os.path.join(MODELS_DIR, "cache")
    if not os.path.isdir(cache):
        return []
    try:
        return [
            dir_name_to_model_id(d)
            for d in os.listdir(cache)
            if d.startswith("models--") and os.path.isdir(os.path.join(cache, d))
        ]
    except Exception as scan_err:
        logger.error(f"Cache scan failed: {scan_err}")
        return []


# ---------------------------------------------------------------------------
# Pydantic models (warnings silenced)
# ---------------------------------------------------------------------------
class QueryRequest(BaseModel):
    prompt: str
    model_id: Optional[str] = Field(None, description="Model ID or alias")
    temperature: float = Field(0.7, ge=0.0, le=1.0)
    max_tokens: int = Field(150, ge=1, le=2048)

    class Config:
        protected_namespaces = ()


class QueryResponse(BaseModel):
    command: Optional[Dict[str, Any]] = None
    raw_generation: str = ""
    model_used: str = ""
    error: Optional[str] = None

    class Config:
        protected_namespaces = ()

    model_config = {
        "json_schema_extra": {
            "example": {
                "command": {"device": "lights", "location": "kitchen", "action": "turn_on"},
                "raw_generation": "{\"device\":\"lights\",...}",
                "model_used": "tinyllama",
                "error": None,
            }
        }
    }


class ModelInfo(BaseModel):
    model_id: str
    is_loaded: bool
    is_current: bool = False
    model_type: str = ""

    class Config:
        protected_namespaces = ()

# ---------------------------------------------------------------------------
# Model lifecycle (load/unload)
# ---------------------------------------------------------------------------
async def unload_model(model_id: str) -> bool:
    global current_model_id
    full_id = MODEL_ALIASES.get(model_id.lower(), model_id)
    async with model_lock:
        if full_id not in loaded_models:
            return False
        bundle = loaded_models.pop(full_id)
        try:
            if hasattr(bundle["model"], "to"):
                bundle["model"].to("cpu")
            del bundle
            gc.collect()
            if DEVICE == "cuda":
                torch.cuda.empty_cache(); torch.cuda.synchronize()
        finally:
            if current_model_id == full_id:
                current_model_id = None
        return True


async def load_model(model_id: str) -> None:
    global current_model_id
    full_id = MODEL_ALIASES.get(model_id.lower(), model_id)
    async with model_lock:
        if full_id in loaded_models:
            current_model_id = full_id
            return
        if current_model_id:
            await unload_model(current_model_id)
        logger.info(f"Loading {full_id} …")
        kwargs = {"trust_remote_code": True, "cache_dir": os.path.join(MODELS_DIR, "cache")}
        tokenizer = AutoTokenizer.from_pretrained(full_id, **kwargs)
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token or tokenizer.add_special_tokens({"pad_token": "[PAD]"})
        if DEVICE == "cuda":
            kwargs.update({"device_map": "auto", "torch_dtype": torch.float16})
        else:
            kwargs.update({"device_map": None, "torch_dtype": torch.float32})
        model = AutoModelForCausalLM.from_pretrained(full_id, **kwargs)
        if tokenizer.pad_token == "[PAD]":
            model.resize_token_embeddings(len(tokenizer))
        loaded_models[full_id] = {"model": model, "tokenizer": tokenizer, "loaded_at": datetime.utcnow()}
        current_model_id = full_id

# ---------------------------------------------------------------------------
# Text generation helper
# ---------------------------------------------------------------------------
async def generate_raw_text(model, tokenizer, prompt: str, temperature: float, max_tokens: int) -> str:
    try:
        encoded = tokenizer(prompt, return_tensors="pt", padding=True, truncation=True, max_length=tokenizer.model_max_length)
        if "token_type_ids" not in tokenizer.model_input_names:
            encoded.pop("token_type_ids", None)
        inputs = {k: v.to(DEVICE) for k, v in encoded.items()}
        with torch.no_grad():
            out = model.generate(**inputs, max_new_tokens=max_tokens, temperature=temperature, do_sample=True, pad_token_id=tokenizer.eos_token_id)
        return tokenizer.decode(out[0], skip_special_tokens=True)
    except Exception as e:
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Generation failed: {e}")

# ---------------------------------------------------------------------------
# FastAPI app & endpoints
# ---------------------------------------------------------------------------
app = FastAPI(title="Voice Service – Smart Home Control")


@app.post("/smart-home/command", response_model=QueryResponse)
async def smart_home_command(req: QueryRequest, bg: BackgroundTasks):
    if not req.model_id and not current_model_id:
        for cand in RECOMMENDED_MODELS:
            try:
                await load_model(cand)
                break
            except Exception:
                continue
    if req.model_id:
        await load_model(req.model_id)
    if not current_model_id:
        raise HTTPException(status_code=500, detail="No model available")
    bundle = loaded_models[current_model_id]
    prompt = create_prompt(req.prompt, current_model_id)
    raw = await generate_raw_text(bundle["model"], bundle["tokenizer"], prompt, req.temperature, req.max_tokens)
    try:
        cmd_json = process_command(raw)
        err = None if cmd_json else "Model output lacked valid JSON command"
    except Exception as e:
        cmd_json, err = None, f"Parsing failed: {e}"
    return QueryResponse(command=cmd_json, raw_generation=raw, model_used=current_model_id, error=err)


@app.get("/models", response_model=List[ModelInfo])
async def list_models_endpoint():
    infos = [ModelInfo(model_id=m, is_loaded=True, is_current=(m == current_model_id), model_type="loaded") for m in loaded_models]
    seen = {i.model_id for i in infos}
    for m in list_available_models():
        if m not in seen:
            infos.append(ModelInfo(model_id=m, is_loaded=False))
            seen.add(m)
    for alias, full in MODEL_ALIASES.items():
        if full in seen and alias not in seen:
            infos.append(ModelInfo(model_id=alias, is_loaded=False, model_type="alias"))
            seen.add(alias)
    for rec in RECOMMENDED_MODELS:
        if rec not in seen:
            infos.append(ModelInfo(model_id=rec, is_loaded=False, model_type="recommended"))
    infos.sort(key=lambda x: (not x.is_loaded, x.model_id))
    return infos


@app.get("/load-model")
async def load_model_get(model_id: str):
    await load_model(model_id)
    return {"status": "success", "message": f"Loaded {model_id}"}


@app.get("/unload-model")
async def unload_model_get(model_id: str):
    return {"status": "success" if await unload_model(model_id) else "skipped", "message": f"Unloaded {model_id}"}


@app.get("/memory")
async def memory():
    vm = psutil.virtual_memory()
    info = {"total_ram": vm.total/2**30, "used_ram": vm.used/2**30, "ram_percent": vm.percent}
    if DEVICE == "cuda":
        try:
            props = torch
