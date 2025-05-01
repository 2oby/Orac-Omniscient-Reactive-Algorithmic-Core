#!/usr/bin/env python3
"""
Voice Service - Smart Home Control with JSON Parsing for Structured Output
Fixed & refactored for robustness, concurrency‑safety and CPU/GPU flexibility.
"""

import os
import sys
import json
import time
import gc
import traceback
import logging
from datetime import datetime
from typing import Optional, Dict, Any, List

import asyncio

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
# JSON integration helpers (must exist in PYTHONPATH)
# ---------------------------------------------------------------------------
from response_to_JSON_integration import (
    generate_json_from_response,  # noqa – imported for external use
    create_prompt,
    SmartHomeCommand,
    process_command,
)

# ---------------------------------------------------------------------------
# Configuration & logging
# ---------------------------------------------------------------------------
start_time = time.time()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("/app/logs/voice_service.log"),
    ],
)
logger = logging.getLogger("voice-service")

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
logger.info(f"Using device: {DEVICE}")
if DEVICE == "cuda":
    try:
        props = torch.cuda.get_device_properties(0)
        logger.info(f"GPU: {props.name} | {props.total_memory/1e9:.2f} GB")
    except Exception as gpu_err:  # pragma: no cover – best‑effort log
        logger.warning(f"Could not query GPU properties: {gpu_err}")

# Directories ----------------------------------------------------------------
MODELS_DIR = os.environ.get("MODELS_DIR", "/models")
CONFIG_DIR = os.environ.get("CONFIG_DIR", "config")
os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(CONFIG_DIR, exist_ok=True)
logger.info(f"Models directory: {MODELS_DIR}")
logger.info(f"Config directory: {CONFIG_DIR}")

# Model aliases & recommendations -------------------------------------------
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

# In‑memory state ------------------------------------------------------------
loaded_models: dict[str, dict[str, Any]] = {}
current_model_id: Optional[str] = None
model_lock = Lock()

# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------
class QueryRequest(BaseModel):
    prompt: str
    model_id: Optional[str] = Field(
        None, description="Model ID or alias (e.g. 'gpt2', 'tinyllama')"
    )
    temperature: float = Field(0.7, ge=0.0, le=1.0)
    max_tokens: int = Field(150, gt=0, le=2048)


class QueryResponse(BaseModel):
    command: Optional[Dict[str, Any]] = None
    raw_generation: str = ""
    model_used: str = ""
    error: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "command": {
                    "device": "lights",
                    "location": "kitchen",
                    "action": "turn_on",
                    "value": None,
                },
                "raw_generation": "{\"device\": \"lights\", \"location\": \"kitchen\", \"action\": \"turn_on\", \"value\": null}",
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


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def model_id_to_dir_name(model_id: str) -> str:
    """Convert a HF model ID to the huggingface‑cache directory name."""
    return "models--" + "--".join(model_id.split("/"))


def dir_name_to_model_id(dir_name: str) -> str:
    if not dir_name.startswith("models--"):
        return dir_name
    return "/".join(dir_name[len("models--") :].split("--"))


def list_available_models() -> List[str]:
    cache_dir = os.path.join(MODELS_DIR, "cache")
    if not os.path.isdir(cache_dir):
        return []
    try:
        return [
            dir_name_to_model_id(d)
            for d in os.listdir(cache_dir)
            if d.startswith("models--") and os.path.isdir(os.path.join(cache_dir, d))
        ]
    except Exception as scan_err:
        logger.error(f"Error scanning cache dir: {scan_err}")
        return []


def is_model_available(model_id: str) -> bool:
    full_id = MODEL_ALIASES.get(model_id.lower(), model_id)
    path = os.path.join(MODELS_DIR, "cache", model_id_to_dir_name(full_id))
    return os.path.isdir(path)


# ---------------------------------------------------------------------------
# Model lifecycle
# ---------------------------------------------------------------------------
async def unload_model(model_id: str) -> bool:
    """Unload model from memory to free VRAM/RAM."""
    global current_model_id
    full_id = MODEL_ALIASES.get(model_id.lower(), model_id)

    async with model_lock:
        if full_id not in loaded_models:
            logger.info("Model not loaded — nothing to unload")
            return False

        logger.info(f"Unloading model {full_id}")
        model = loaded_models[full_id]["model"]
        tokenizer = loaded_models[full_id]["tokenizer"]

        try:
            if hasattr(model, "to"):
                model.to("cpu")
            del model, tokenizer, loaded_models[full_id]
            gc.collect()
            if DEVICE == "cuda":
                torch.cuda.empty_cache()
                torch.cuda.synchronize()
            if current_model_id == full_id:
                current_model_id = None
            return True
        except Exception as unload_err:
            logger.error(f"Failed to unload {full_id}: {unload_err}")
            logger.error(traceback.format_exc())
            return False


async def load_model(model_id: str) -> None:
    """Load a model or switch to an already‑loaded one."""
    global current_model_id
    full_id = MODEL_ALIASES.get(model_id.lower(), model_id)

    async with model_lock:
        if full_id in loaded_models:
            current_model_id = full_id
            logger.info(f"Model {full_id} already in memory — switched context")
            return

        if current_model_id:
            await unload_model(current_model_id)

        logger.info(f"Loading model {full_id}…")
        try:
            tokenizer = AutoTokenizer.from_pretrained(
                full_id,
                trust_remote_code=True,
                cache_dir=os.path.join(MODELS_DIR, "cache"),
                use_fast=True,
            )
            if tokenizer.pad_token is None:
                tokenizer.pad_token = tokenizer.eos_token or tokenizer.add_special_tokens(
                    {"pad_token": "[PAD]"}
                )

            model_kwargs = {
                "trust_remote_code": True,
                "cache_dir": os.path.join(MODELS_DIR, "cache"),
            }
            if DEVICE == "cuda":
                model_kwargs.update(
                    {
                        "device_map": "auto",
                        "torch_dtype": torch.float16,
                    }
                )
            else:
                model_kwargs.update({"device_map": None, "torch_dtype": torch.float32})

            model = AutoModelForCausalLM.from_pretrained(full_id, **model_kwargs)
            if tokenizer.pad_token == "[PAD]":
                model.resize_token_embeddings(len(tokenizer))

            # Keep bookkeeping
            loaded_models[full_id] = {
                "model": model,
                "tokenizer": tokenizer,
                "loaded_at": datetime.utcnow(),
            }
            current_model_id = full_id

            # Log VRAM usage if GPU
            if DEVICE == "cuda":
                free, total = torch.cuda.mem_get_info()
                logger.info(
                    f"VRAM used: {(total-free)/1e9:.2f}/{total/1e9:.2f} GB "
                    f"({(1-free/total)*100:.1f} %)"
                )

        except Exception as load_err:
            logger.error(f"Could not load {full_id}: {load_err}")
            logger.error(traceback.format_exc())
            raise HTTPException(status_code=500, detail=str(load_err))


# ---------------------------------------------------------------------------
# Text generation helper
# ---------------------------------------------------------------------------
async def generate_raw_text(
    model: Any,
    tokenizer: Any,
    prompt: str,
    temperature: float = 0.7,
    max_tokens: int = 100,
) -> str:
    try:
        raw_inputs = tokenizer(
            prompt,
            return_tensors="pt",
            padding=True,
            truncation=True,
            max_length=tokenizer.model_max_length,
        )
        if "token_type_ids" not in tokenizer.model_input_names:
            raw_inputs.pop("token_type_ids", None)
        inputs = {k: v.to(DEVICE) for k, v in raw_inputs.items()}
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                temperature=temperature,
                do_sample=True,
                pad_token_id=tokenizer.eos_token_id,
            )
        return tokenizer.decode(outputs[0], skip_special_tokens=True)
    except Exception as gen_err:
        logger.error(f"Text generation failed: {gen_err}")
        logger.error(traceback.format_exc())
        raise


# ---------------------------------------------------------------------------
# FastAPI setup
# ---------------------------------------------------------------------------
app = FastAPI(title="Voice Service – Smart Home Control")


@app.post("/smart-home/command", response_model=QueryResponse)
async def generate_smart_home_command(req: QueryRequest, bg: BackgroundTasks):
    logger.info(f"Incoming request: {req.model_dump()}")

    if not req.model_id and not current_model_id:
        for candidate in RECOMMENDED_MODELS:
            try:
                await load_model(candidate)
                req.model_id = candidate
                break
            except HTTPException:
                continue
        if not current_model_id:
            raise HTTPException(status_code=500, detail="No model available")

    if req.model_id:
        await load_model(req.model_id)

    assert current_model_id and current_model_id in loaded_models  # sanity
    model_bundle = loaded_models[current_model_id]

    prompt = create_prompt(req.prompt, current_model_id)
    raw_text = await generate_raw_text(
        model_bundle["model"],
        model_bundle["tokenizer"],
        prompt,
        req.temperature,
        req.max_tokens,
    )

    command_json: Optional[Dict[str, Any]] = None
    error_msg: Optional[str] = None
    try:
        command_json = process_command(raw_text)
        if not command_json:
            error_msg = "Model output did not contain valid JSON command"
    except Exception as pc_err:
        error_msg = f"Command parsing failed: {pc_err}"
        logger.error(error_msg)
        logger.error(traceback.format_exc())

    return QueryResponse(
        command=command_json,
        raw_generation=raw_text,
        model_used=current_model_id,
        error=error_msg,
    )


# ---------------------------------------------------------------------------
# Admin & misc endpoints
# ---------------------------------------------------------------------------
@app.get("/models", response_model=List[ModelInfo])
async def list_models_endpoint():
    infos: list[ModelInfo] = [
        ModelInfo(
            model_id=m_id,
            is_loaded=True,
            is_current=(m_id == current_model_id),
            model_type=loaded_models[m_id].get("type", "loaded"),
        )
        for m_id in loaded_models
    ]
    seen = {i.model_id for i in infos}
    for m_id in list_available_models():
        if m_id not in seen:
            infos.append(ModelInfo(model_id=m_id, is_loaded=False))
            seen.add(m_id)
    for alias, full in MODEL_ALIASES.items():
        if alias not in seen and full in seen:
            infos.append(ModelInfo(model_id=alias, is_loaded=False, model_type="alias"))
            seen.add(alias)
    for rec in RECOMMENDED_MODELS:
        if rec not in seen:
            infos.append(ModelInfo(model_id=rec, is_loaded=False, model_type="recommended"))
    infos.sort(key=lambda x: (not x.is_loaded, x.model_id))
    return infos


@app.get("/load-model")
async def load_model_endpoint(model_id: str):
    await load_model(model_id)
    return {"status": "success", "message": f"Loaded {model_id}"}


@app.get("/unload-model")
async def unload_model_endpoint(model_id: str):
    if await unload_model(model_id):
        return {"status": "success", "message": f"Unloaded {model_id}"}
    return {"status": "skipped", "message": f"Model {model_id} not loaded"}


@app.get("/memory")
async def memory_info():
    vm = psutil.virtual_memory()
    info: Dict[str, Any] = {
        "total_ram": vm.total / 2 ** 30,
        "available_ram": vm.available / 2 ** 30,
        "used_ram": vm.used / 2 ** 30,
        "ram_percent": vm.percent,
    }
    if DEVICE == "cuda":
        try:
            props = torch.cuda.get_device_properties(0)
            used = torch.cuda.memory_allocated() / 2 ** 30
            info.update(
                {
                    "total_gpu": props.total_memory / 2 ** 30,
                    "used_gpu": used,
                    "gpu_percent": used / (props.total_memory / 2 ** 30) * 100,
                }
            )
        except Exception as gpu_mem_err:
            logger.warning(f"GPU memory query failed: {gpu_mem_err}")
    return info


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "device": DEVICE,
        "loaded_models": list(loaded_models),
        "current_model": current_model_id,
    }


@app.get("/simple-test")
async def simple_test():
    return {
        "status": "ok",
        "timestamp": datetime.utcnow().isoformat(),
    }


# ---------------------------------------------------------------------------
# Root endpoint – HTML/CLI dashboard
# ---------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    models_info = await list_models_endpoint()
    table_rows = [
        (m.model_id, "LOADED" if m.is_loaded else "……", m.model_type) for m in models_info
    ]

    uptime = time.time() - start_time
    uptime_str = f"{int(uptime//3600)}h {int(uptime%3600//60)}m {int(uptime%60)}s"

    libs = {lib: pkg_resources.get_distribution(lib).version for lib in [
        "fastapi",
        "uvicorn",
        "torch",
        "transformers",
        "psutil",
    ]}

    mem = await memory_info()
    gpu_info = (
        f"GPU total/used: {mem.get('total_gpu', 0):.2f}/{mem.get('used_gpu', 0):.2f} GB "
        f"({mem.get('gpu_percent', 0):.1f} %)" if DEVICE == "cuda" else "GPU: not available"
    )

    debug_metrics = [
        ("Uptime", uptime_str),
        ("Device", DEVICE),
        ("GPU", gpu_info),
        (
            "RAM",
            f"{mem['used_ram']:.2f}/{mem['total_ram']:.2f} GB ({mem['ram_percent']:.1f} %)",
        ),
        ("Python", sys.version.split()[0]),
        *[(k.capitalize(), v) for k, v in libs.items()],
        ("Current model", current_model_id or "None"),
        ("Log", "/app/logs/voice_service.log"),
    ]

    accept = request.headers.get("accept", "").lower()
    wants_html = "text/html" in accept or "*/*" in accept or not accept

    if not wants_html:
        # Plain‑text for curl
        max_model = max(len(r[0]) for r in table_rows) if table_rows else 10
        text = "ORAC – Omniscient Reactive Algorithmic Core\n\nAvailable models\n"
        text += f"{'ID':<{max_model}}  Status  Type\n" + "-" * (max_model + 13) + "\n"
        for mid, stat, typ in table_rows:
            text += f"{mid:<{max_model}}  {stat:<6}  {typ}\n"
        text += "\nSystem info\n" + "-" * 30 + "\n"
        max_label = max(len(m[0]) for m in debug_metrics)
        for label, val in debug_metrics:
            text += f"{label:<{max_label}} : {val}\n"
        return PlainTextResponse(text)

    # --- HTML response ---
    html = """
    <html><head><title>ORAC – Voice Service</title><style>
        body{font-family:Arial,Helvetica,sans-serif;margin:20px}
        table{border-collapse:collapse;margin-bottom:20px;width:90%}
        th,td{border:1px solid #ddd;padding:8px;text-align:left}
        th{background:#f2f2f2}
        .loaded{color:#4caf50;font-weight:bold}
        .btn{padding:4px 8px;border:none;border-radius:4px;cursor:pointer;font-size:12px}
        .load{background:#4caf50;color:#fff}.unload{background:#f44336;color:#fff}
        .btn:disabled{background:#ccc;cursor:not-allowed}
        #msg{margin:10px 0;padding:8px;border-radius:4px;display:none}
        #msg.success{background:#dff0d8;color:#3c763d}
        #msg.error{background:#f2dede;color:#a94442}
        .monospace{font-family:monospace;white-space:pre-wrap;background:#f0f0f0;padding:8px;border-radius:4px}
    </style></head><body>
        <h2>ORAC – Omniscient Reactive Algorithmic Core</h2>
        <div id='msg'></div>
        <h3>Test prompt</h3>
        <input id='prompt' style='width:70%;padding:6px'>
        <button id='send' class='btn load' onclick='send()'>Test</button>
        <div id='resp' style='display:none'>
            <h4>Command JSON</h4><div id='cmd' class='monospace'></div>
            <h4>Raw model output</h4><div id='raw' class='monospace'></div>
            <div id='err' class='monospace' style='color:#f44336'></div>
        </div>
        <h3>Models</h3><table><tr><th>ID</th><th>Status</th><th>Type</th><th>Action</th></tr>"""
    for mid, stat, typ in table_rows:
        loaded = stat == "LOADED"
        html += f"<tr><td>{mid}</td><td class={'loaded' if loaded else ''}>{stat}</td><td>{typ}</td><td>"
        html += (
            f"<button class='btn load' onclick=act('{mid}','load') {'disabled' if loaded else ''}>Load</button>"
            f" <button class='btn unload' onclick=act('{mid}','unload') {'disabled' if not loaded else ''}>Unload</button>"
        )
        html += "</td></tr>"
    html += "</table><h3>System info</h3><table>"
    for label, val in debug_metrics:
        html += f"<tr><td>{label}</td><td>{val}</td></tr>"
    html += "</table>"

    # JS helpers
    html += """
    <script>
    async function act(id,action){
        const res=await fetch(`/${action}-model?model_id=`+encodeURIComponent(id));
        const data=await res.json();
        const m=document.getElementById('msg');
        m.textContent=data.message||data.detail;m.className=res.ok?'success':'error';m.style.display='block';
        setTimeout(()=>location.reload(),1000);
    }
    async function send(){
        const btn=document.getElementById('send');btn.disabled=true;btn.textContent='…';
        const body={prompt:document.getElementById('prompt').value,temperature:0.7,max_tokens:150};
        const r=await fetch('/smart-home/command',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
        const d=await r.json();
        document.getElementById('resp').style.display='block';
        document.getElementById('cmd').textContent=d.command?JSON.stringify(d.command,null,2):'';
        document.getElementById('raw').textContent=d.raw_generation||'';
        document.getElementById('err').textContent=d.error||'';
        btn.disabled=false;btn.textContent='Test';
    }
    </script></body></html>"""

    return HTMLResponse(html)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    # Only run the dev server if launched directly (docker/Kubernetes will usually run uvicorn externally)
    logger.info("Starting development server on http://0.0.0.0:8000 …")
    uvicorn.run("voice_service_fixed:app", host="0.0.0.0", port=8000, reload=False)
