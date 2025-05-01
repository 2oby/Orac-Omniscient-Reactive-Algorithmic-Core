#!/usr/bin/env python3
"""
Voice Service - Smart Home Control with JSON Parsing for Structured Output
"""

import os
import json
import torch
import logging
import psutil
import sys
import traceback
import uvicorn
import asyncio

import time
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi import Request
import pkg_resources

from typing import Optional, Dict, Any, List
from fastapi import FastAPI, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field
from transformers import AutoModelForCausalLM, AutoTokenizer
from asyncio import Lock


# Import JSON integration module (assumed to exist)
from response_to_JSON_integration import (
    generate_json_from_response, 
    create_prompt, 
    SmartHomeCommand
)

# Track server start time for uptime calculation
start_time = time.time()


# Configure logging with detailed traceback
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("/app/logs/voice_service.log")
    ]
)
logger = logging.getLogger("voice-service")

app = FastAPI(title="Voice Service - Smart Home Control")

DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
logger.info(f"Using device: {DEVICE}")

if DEVICE == "cuda":
    try:
        device_props = torch.cuda.get_device_properties(0)
        logger.info(f"GPU: {device_props.name}")
        logger.info(f"Total GPU memory: {device_props.total_memory / 1e9:.2f} GB")
    except Exception as e:
        logger.error(f"Failed to get GPU info: {e}")

MODELS_DIR = os.environ.get("MODELS_DIR", "/models")
CONFIG_DIR = os.environ.get("CONFIG_DIR", "config")
os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(CONFIG_DIR, exist_ok=True)
logger.info(f"Using models directory: {MODELS_DIR}")
logger.info(f"Using config directory: {CONFIG_DIR}")

# Map short names to full model IDs
MODEL_ALIASES = {
    "tinyllama": "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
    "pythia": "EleutherAI/pythia-70m",
    "phi2": "microsoft/phi-2",
    "mistral": "nilq/mistral-1L-tiny",
    "qwen": "Qwen/Qwen1.5-0.5B-Chat",
    "qwen3-1.7b": "Qwen/Qwen3-1.7B-FP8",
    "qwen3-0.6b": "Qwen/Qwen3-0.6B",
    "qwen3-0.6b-fp8": "Qwen/Qwen3-0.6B-FP8"
}

# Updated list with aliases, prioritizing TinyLlama for better performance
RECOMMENDED_MODELS = ["tinyllama", "qwen3-0.6b-fp8", "qwen3-0.6b", "qwen3-1.7b", "distilgpt2", "gpt2"]

loaded_models = {}
current_model_id = None
model_lock = Lock()  # Lock for synchronizing model load/unload operations

class QueryRequest(BaseModel):
    prompt: str
    model_id: Optional[str] = Field(None, description="Model ID (e.g., 'gpt2', 'distilgpt2')")
    temperature: float = Field(0.7, description="Temperature for generation (0.0-1.0)")
    max_tokens: int = Field(150, description="Maximum number of tokens to generate")

class QueryResponse(BaseModel):
    command: Optional[Dict[str, Any]] = None
    raw_generation: str = ""
    model_used: str = ""
    error: Optional[str] = None

    model_config = {
        "json_schema_extra": {
            "example": {
                "command": {"device": "lights", "location": "kitchen", "action": "turn_on", "value": None},
                "raw_generation": "{\"device\": \"lights\", \"location\": \"kitchen\", \"action\": \"turn_on\", \"value\": null}",
                "model_used": "tinyllama",
                "error": None
            }
        }
    }

class ModelInfo(BaseModel):
    model_id: str
    is_loaded: bool
    is_current: bool = False
    model_type: str = ""

class MemoryInfo(BaseModel):
    total_ram: float
    available_ram: float
    used_ram: float
    ram_percent: float
    total_gpu: Optional[float] = None
    used_gpu: Optional[float] = None
    gpu_percent: Optional[float] = None

# Helper functions for model ID conversion and checking
def model_id_to_dir_name(model_id: str) -> str:
    if "/" in model_id:
        parts = model_id.split("/")
        return f"models--" + "--".join(parts)
    else:
        return f"models--{model_id}"

def dir_name_to_model_id(dir_name: str) -> str:
    if not dir_name.startswith("models--"):
        return dir_name
    parts = dir_name[len("models--"):].split("--")
    if len(parts) == 1:
        return parts[0]
    else:
        return f"{parts[0]}/{'/'.join(parts[1:])}"

def list_available_models() -> List[str]:
    available_models = []
    cache_dir = os.path.join(MODELS_DIR, "cache")
    if not os.path.exists(cache_dir):
        return available_models
    try:
        for item in os.listdir(cache_dir):
            if os.path.isdir(os.path.join(cache_dir, item)) and item.startswith("models--"):
                model_id = dir_name_to_model_id(item)
                available_models.append(model_id)
    except Exception as e:
        logger.error(f"Error scanning cache directory: {e}")
    return available_models

def is_model_available(model_id: str) -> bool:
    full_model_id = MODEL_ALIASES.get(model_id.lower(), model_id)
    dir_name = model_id_to_dir_name(full_model_id)
    cache_dir = os.path.join(MODELS_DIR, "cache")
    model_dir = os.path.join(cache_dir, dir_name)
    logger.debug(f"Checking if model exists: {full_model_id} (looking for dir: {dir_name})")
    exists = os.path.isdir(model_dir)
    if not exists and os.path.exists(cache_dir):
        available_models = list_available_models()
        for available_model in available_models:
            if available_model.lower() == full_model_id.lower():
                logger.debug(f"Found model {full_model_id} using fallback check")
                return True
    logger.debug(f"Model {full_model_id} available: {exists}")
    return exists

async def unload_model(model_id: str):
    global loaded_models, current_model_id
    full_model_id = MODEL_ALIASES.get(model_id.lower(), model_id)
    
    async with model_lock:
        if full_model_id not in loaded_models:
            logger.info(f"Model {full_model_id} not loaded, skipping unload")
            return False
        
        logger.info(f"Unloading model: {full_model_id}")
        try:
            # Get references to model and tokenizer
            model = loaded_models[full_model_id]["model"]
            tokenizer = loaded_models[full_model_id]["tokenizer"]
            
            # Move model to CPU before deletion to ensure CUDA memory is freed
            if hasattr(model, 'to'):
                model.to('cpu')
            
            # Delete model and tokenizer
            del model
            del tokenizer
            
            # Remove from loaded_models
            del loaded_models[full_model_id]
            
            # Force garbage collection
            import gc
            gc.collect()
            
            # Clear CUDA cache if using GPU
            if DEVICE == "cuda":
                torch.cuda.empty_cache()
                torch.cuda.synchronize()  # Ensure CUDA operations complete
            
            # Update current_model_id if needed
            if current_model_id == full_model_id:
                current_model_id = None
            
            logger.info(f"Successfully unloaded model: {full_model_id}")
            return True
        except Exception as e:
            logger.error(f"Error unloading model {full_model_id}: {e}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            return False

async def load_model(model_id: str, force_reload: bool = False):
    global loaded_models, current_model_id
    full_model_id = MODEL_ALIASES.get(model_id.lower(), model_id)
    logger.info(f"Requested model: {model_id}, using: {full_model_id}")
    
    async with model_lock:
        if full_model_id in loaded_models and not force_reload:
            logger.info(f"Using cached model: {full_model_id}")
            current_model_id = full_model_id
            return loaded_models[full_model_id]["model"], loaded_models[full_model_id]["tokenizer"]
        
        if current_model_id and current_model_id != full_model_id:
            logger.info(f"Unloading current model {current_model_id} to load {full_model_id}")
            await unload_model(current_model_id)
        
        if not is_model_available(full_model_id):
            logger.info(f"Model {full_model_id} not found in cache, attempting to download...")
            try:
                # Try to download the model
                tokenizer = AutoTokenizer.from_pretrained(
                    full_model_id,
                    cache_dir=os.path.join(MODELS_DIR, "cache"),
                    padding_side="left"
                )
                model = AutoModelForCausalLM.from_pretrained(
                    full_model_id,
                    cache_dir=os.path.join(MODELS_DIR, "cache"),
                    torch_dtype=torch.float16,
                    low_cpu_mem_usage=True,
                    device_map="auto"
                )
                logger.info(f"Successfully downloaded model: {full_model_id}")
            except Exception as e:
                logger.error(f"Failed to download model {full_model_id}: {str(e)}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to download model: {str(e)}"
                )
        
        logger.info(f"Loading model: {full_model_id}")
        try:
            logger.info(f"Step 1: Loading tokenizer for {full_model_id}...")
            tokenizer = AutoTokenizer.from_pretrained(
                full_model_id, 
                cache_dir=os.path.join(MODELS_DIR, "cache"), 
                padding_side="left",
                local_files_only=True
            )
            logger.info("Step 1 COMPLETE: Tokenizer loaded.")
            
            logger.info("Step 2: Setting pad token and fixing tokenizer attributes...")
            if tokenizer.pad_token is None:
                tokenizer.pad_token = tokenizer.eos_token or "</s>"
            if not hasattr(tokenizer, 'vocabulary'):
                tokenizer.vocabulary = tokenizer.get_vocab() if hasattr(tokenizer, 'get_vocab') else tokenizer.encoder
                logger.info(f"Added vocabulary from get_vocab with {len(tokenizer.vocabulary)} items")
            logger.info(f"Step 2 COMPLETE: Pad token set to '{tokenizer.pad_token}' and tokenizer attributes fixed.")
            
            logger.info(f"Step 3: Loading model weights for {full_model_id}...")
            if DEVICE == "cuda":
                before_load = torch.cuda.mem_get_info()[0] / (1024 ** 3)
                logger.info(f"Available memory before loading model: {before_load:.2f} GB")
            
            model = AutoModelForCausalLM.from_pretrained(
                full_model_id,
                cache_dir=os.path.join(MODELS_DIR, "cache"),
                torch_dtype=torch.float16,
                low_cpu_mem_usage=True,
                device_map="auto",
                local_files_only=True,
            )
            model.to(DEVICE)
            model.eval()
            logger.info(f"Model moved to device: {DEVICE}")
            
            if DEVICE == "cuda":
                after_load = torch.cuda.mem_get_info()[0] / (1024 ** 3)
                logger.info(f"Available memory after loading model: {after_load:.2f} GB")
                logger.info(f"Memory used by model: {before_load - after_load:.2f} GB")
            
            logger.info("Step 3 COMPLETE: Model weights loaded.")
            
            model_type = model.config.model_type if hasattr(model.config, 'model_type') else "unknown"
            loaded_models[full_model_id] = {"model": model, "tokenizer": tokenizer, "type": model_type}
            current_model_id = full_model_id
            logger.info(f"Successfully loaded model: {full_model_id} (Type: {model_type})")
            return model, tokenizer
        except Exception as e:
            logger.error(f"Error loading model {full_model_id}: {str(e)}")
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise HTTPException(status_code=500, detail=f"Failed to load model: {str(e)}")

async def generate_raw_text(model, tokenizer, prompt: str, temperature: float = 0.7, max_tokens: int = 150):
    logger.info(f"Generating raw text with temperature={temperature}, max_tokens={max_tokens}")
    try:
        inputs = tokenizer(prompt, return_tensors="pt", padding=True).to(DEVICE)
        logger.debug("Inputs prepared for generation")
        
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                temperature=temperature,
                do_sample=True,
                top_k=50,
                top_p=0.95,
                pad_token_id=tokenizer.pad_token_id,
                eos_token_id=tokenizer.eos_token_id
            )
        
        raw_text = tokenizer.decode(outputs[0], skip_special_tokens=True)
        if raw_text.startswith(prompt):
            raw_text = raw_text[len(prompt):].strip()
        logger.info(f"Raw generation complete: {raw_text[:100]}..." if len(raw_text) > 100 else f"Raw generation complete: {raw_text}")
        return raw_text
    except Exception as e:
        logger.error(f"Error in raw text generation: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise e

@app.post("/smart-home/command", response_model=QueryResponse)
async def generate_smart_home_command(request: QueryRequest, background_tasks: BackgroundTasks):
    logger.info(f"Received request: {request.model_dump()}")
    model_used = request.model_id or "default"
    
    try:
        if not request.model_id:
            # If no model specified, use current model if one is loaded
            if current_model_id:
                model_used = current_model_id
                logger.info(f"Using currently loaded model: {current_model_id}")
            else:
                # Try to load a recommended model if none is loaded
                for model_id in RECOMMENDED_MODELS:
                    try:
                        await load_model(model_id)
                        request.model_id = model_id
                        model_used = model_id
                        break
                    except Exception as e:
                        logger.warning(f"Failed to load recommended model {model_id}: {e}")
                if not request.model_id or not current_model_id:
                    raise HTTPException(status_code=500, detail="Could not find a suitable model")
        else:
            # If a specific model is requested, load it
            await load_model(request.model_id)
            model_used = request.model_id
            if request.model_id.lower() in MODEL_ALIASES:
                model_used = f"{request.model_id} ({MODEL_ALIASES[request.model_id.lower()]})"
        
        if not current_model_id or current_model_id not in loaded_models:
            raise HTTPException(status_code=500, detail="No model is currently loaded")
        
        model = loaded_models[current_model_id]["model"]
        tokenizer = loaded_models[current_model_id]["tokenizer"]
        
        prompt = f"""Convert this command to JSON: "{request.prompt}"

Output format:
{{
  "device": string,  // The device (lights, tv, etc.)
  "location": string | null,  // Location or null
  "action": string,  // Action (turn_on, set, etc.)
  "value": string | null  // Value or null
}}

Examples:
1. "Turn on the kitchen lights" -> {{"device": "lights", "location": "kitchen", "action": "turn_on", "value": null}}
2. "Set thermostat to 72" -> {{"device": "thermostat", "location": null, "action": "set", "value": "72"}}
3. "Turn off the TV" -> {{"device": "tv", "location": null, "action": "turn_off", "value": null}}

JSON OUTPUT:
"""
        logger.info(f"Created prompt: {prompt}")
        
        command_json = None
        error_msg = None
        raw_text = ""
        
        try:
            raw_text = await generate_raw_text(
                model, 
                tokenizer, 
                prompt, 
                request.temperature, 
                request.max_tokens
            )
        except Exception as e:
            logger.error(f"Raw text generation failed: {str(e)}")
            error_msg = f"Raw text generation failed: {str(e)}"
            return {
                "command": None,
                "raw_generation": "",
                "model_used": model_used,
                "error": error_msg
            }
        
        logger.info("Using regex-based parsing for structured output...")
        try:
            command_json = await generate_json_from_response(raw_text)
            if not command_json:
                logger.warning("Regex parsing failed, attempting fallback...")
                import re
                json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
                if json_match:
                    command_json = json.loads(json_match.group(0))
                    logger.info(f"Fallback parsing succeeded: {command_json}")
                else:
                    error_msg = "Failed to extract valid command from model output"
        except Exception as e:
            logger.error(f"JSON parsing failed: {str(e)}")
            error_msg = f"Failed to parse JSON: {str(e)}"
        
        response = {
            "command": command_json,
            "raw_generation": raw_text,
            "model_used": model_used,
            "error": error_msg
        }
        logger.info(f"Returning response with command: {json.dumps(command_json) if command_json else None}")
        return response
    except Exception as e:
        logger.error(f"Error processing request: {str(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        return {
            "command": None, 
            "raw_generation": "", 
            "model_used": model_used, 
            "error": str(e)
        }

@app.get("/models", response_model=List[ModelInfo])
async def list_models():
    loaded_model_infos = [
        ModelInfo(
            model_id=model_id,
            is_loaded=True,
            is_current=(model_id == current_model_id),
            model_type=loaded_models[model_id].get("type", "unknown")
        ) for model_id in loaded_models
    ]
    all_model_ids = {model.model_id for model in loaded_model_infos}
    available_models = list_available_models()
    logger.info(f"Found {len(available_models)} models in cache: {available_models}")
    
    for model_id in available_models:
        if model_id not in all_model_ids:
            loaded_model_infos.append(
                ModelInfo(
                    model_id=model_id,
                    is_loaded=False,
                    is_current=False,
                    model_type="unknown"
                )
            )
            all_model_ids.add(model_id)
    
    alias_infos = []
    for model_id in all_model_ids.copy():
        for alias, full_id in MODEL_ALIASES.items():
            if full_id == model_id and alias not in all_model_ids:
                alias_infos.append(
                    ModelInfo(
                        model_id=alias,
                        is_loaded=False,
                        is_current=False,
                        model_type="alias"
                    )
                )
                all_model_ids.add(alias)
    
    for model_id in RECOMMENDED_MODELS:
        if model_id not in all_model_ids:
            loaded_model_infos.append(
                ModelInfo(
                    model_id=model_id,
                    is_loaded=False,
                    is_current=False,
                    model_type="recommended"
                )
            )
            all_model_ids.add(model_id)
    
    final_list = loaded_model_infos + alias_infos
    final_list.sort(key=lambda x: (not x.is_loaded, x.model_id))
    logger.info(f"Returning {len(final_list)} models: {[m.model_id for m in final_list]}")
    return final_list

@app.get("/load-model")
async def load_model_endpoint(model_id: str):
    try:
        await load_model(model_id, force_reload=True)
        return {"status": "success", "message": f"Model {model_id} loaded successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/unload-model")
async def unload_model_endpoint(model_id: str):
    result = await unload_model(model_id)
    if result:
        return {"status": "success", "message": f"Model {model_id} unloaded successfully"}
    return {"status": "skipped", "message": f"Model {model_id} was not loaded"}

@app.get("/memory")
async def memory_info():
    vm = psutil.virtual_memory()
    memory_info = {
        "total_ram": vm.total / (1024 ** 3),
        "available_ram": vm.available / (1024 ** 3),
        "used_ram": vm.used / (1024 ** 3),
        "ram_percent": vm.percent
    }
    if DEVICE == "cuda":
        try:
            gpu_memory = torch.cuda.get_device_properties(0).total_memory
            gpu_memory_allocated = torch.cuda.memory_allocated()
            memory_info["total_gpu"] = gpu_memory / (1024 ** 3)
            memory_info["used_gpu"] = gpu_memory_allocated / (1024 ** 3)
            memory_info["gpu_percent"] = (gpu_memory_allocated / gpu_memory) * 100
        except Exception as e:
            logger.error(f"Error getting GPU memory info: {e}")
    return memory_info

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "voice-service",
        "device": DEVICE,
        "loaded_models": list(loaded_models.keys()),
        "current_model": current_model_id
    }

@app.get("/simple-test")
async def simple_test():
    return {
        "status": "ok",
        "message": "API is responding correctly",
        "timestamp": str(asyncio.get_event_loop().time())
    }

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Display a table of models and debug info, formatted for browser or curl."""
    # Gather model information
    models_info = await list_models()  # Reuse existing endpoint logic
    model_table = []
    for model in models_info:
        status = "LOADED" if model.is_loaded else "...."
        model_table.append((model.model_id, status, model.model_type))

    # Gather debug information
    uptime_seconds = time.time() - start_time
    uptime_str = f"{int(uptime_seconds // 3600)}h {int((uptime_seconds % 3600) // 60)}m {int(uptime_seconds % 60)}s"
    
    # Library versions
    libraries = {
        "fastapi": pkg_resources.get_distribution("fastapi").version,
        "uvicorn": pkg_resources.get_distribution("uvicorn").version,
        "torch": pkg_resources.get_distribution("torch").version,
        "transformers": pkg_resources.get_distribution("transformers").version,
        "psutil": pkg_resources.get_distribution("psutil").version,
    }
    
    # Memory and GPU info
    memory = await memory_info()
    gpu_info = f"GPU: {DEVICE}" if DEVICE == "cuda" else "GPU: Not available"
    if DEVICE == "cuda":
        gpu_info += f", Total: {memory['total_gpu']:.2f} GB, Used: {memory['used_gpu']:.2f} GB ({memory['gpu_percent']:.1f}%)"

    debug_info = [
        ("Uptime", uptime_str),
        ("Device", DEVICE),
        ("GPU Info", gpu_info),
        ("RAM", f"Total: {memory['total_ram']:.2f} GB, Used: {memory['used_ram']:.2f} GB ({memory['ram_percent']:.1f}%)"),
        ("Python Version", sys.version.split()[0]),
        ("FastAPI Version", libraries["fastapi"]),
        ("Uvicorn Version", libraries["uvicorn"]),
        ("PyTorch Version", libraries["torch"]),
        ("Transformers Version", libraries["transformers"]),
        ("Psutil Version", libraries["psutil"]),
        ("Current Model", current_model_id or "None"),
        ("Log File", "/app/logs/voice_service.log"),
    ]

    # Check Accept header to decide response format
    accept_header = request.headers.get("accept", "").lower()
    is_browser = "text/html" in accept_header or "*/ *" in accept_header or not accept_header

    if is_browser:
        # HTML response for browsers
        html_content = """
        <html>
        <head>
            <title>ORAC - Voice Service</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 20px; }
                table { border-collapse: collapse; width: 80%; margin-bottom: 20px; }
                th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
                th { background-color: #f2f2f2; }
                h2 { color: #333; }
            </style>
        </head>
        <body>
            <h2>ORAC - Omniscient Reactive Algorithmic Core</h2>
            <h3>Available Models</h3>
            <table>
                <tr><th>Model ID</th><th>Status</th><th>Type</th></tr>
        """
        for model_id, status, model_type in model_table:
            html_content += f"<tr><td>{model_id}</td><td>{status}</td><td>{model_type}</td></tr>"
        
        html_content += """
            </table>
            <h3>System Information</h3>
            <table>
                <tr><th>Metric</th><th>Value</th></tr>
        """
        for metric, value in debug_info:
            html_content += f"<tr><td>{metric}</td><td>{value}</td></tr>"
        
        html_content += """
            </table>
        </body>
        </html>
        """
        return HTMLResponse(content=html_content)
    
    else:
        # Plain text response for curl
        max_model_len = max(len(model_id) for model_id, _, _ in model_table) if model_table else 10
        max_status_len = 6  # Length of "LOADED" or "...."
        max_type_len = max(len(model_type) for _, _, model_type in model_table) if model_table else 10
        
        text_content = "ORAC - Omniscient Reactive Algorithmic Core\n\n"
        text_content += "Available Models\n"
        text_content += f"{'Model ID':<{max_model_len}}  {'Status':<{max_status_len}}  {'Type':<{max_type_len}}\n"
        text_content += "-" * max_model_len + "  " + "-" * max_status_len + "  " + "-" * max_type_len + "\n"
        
        for model_id, status, model_type in model_table:
            text_content += f"{model_id:<{max_model_len}}  {status:<{max_status_len}}  {model_type:<{max_type_len}}\n"
        
        text_content += "\nSystem Information\n"
        max_metric_len = max(len(metric) for metric, _ in debug_info)
        text_content += f"{'Metric':<{max_metric_len}}  Value\n"
        text_content += "-" * max_metric_len + "  " + "-" * 50 + "\n"
        
        for metric, value in debug_info:
            text_content += f"{metric:<{max_metric_len}}  {value}\n"
        
        return PlainTextResponse(content=text_content)
        

if __name__ == "__main__":
    try:
        logger.info("Starting server...")
        uvicorn.run(app, host="0.0.0.0", port=8000)
    except Exception as e:
        logger.error(f"Server crashed: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        sys.exit(1)
