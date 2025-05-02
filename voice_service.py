#!/usr/bin/env python3
"""
Voice Service – Smart‑Home Control
Fully self‑contained, syntax‑clean (fixed truncated block at /memory) and ready for Docker.
"""

# ---------------- Standard library ----------------
import os, sys, time, gc, json, traceback, logging, asyncio
from datetime import datetime
from typing import Optional, Dict, Any, List, Union
from pathlib import Path

# ---------------- Third‑party ----------------------
import psutil, torch, uvicorn, pkg_resources, yaml
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
from pydantic import BaseModel, Field
from transformers import AutoModelForCausalLM, AutoTokenizer
from asyncio import Lock

# ---------------- GGUF Support --------------------
try:
    from llama_cpp import Llama
    GGUF_AVAILABLE = True
except ImportError:
    GGUF_AVAILABLE = False
    logger.warning("llama-cpp-python not installed. GGUF support disabled.")

# ---------------- Project‑local --------------------
try:
    from response_to_JSON_integration import create_prompt, process_command, load_prompt_template
except ImportError as e:
    logging.warning(f"Original integration module not found: {e}")
    # Define fallback functions
    def load_prompt_template(model_id: str) -> Optional[str]:
        """Load model-specific prompt template from config directory."""
        # Clean the model_id to create a valid filename
        clean_model_id = model_id.replace('/', '_').replace('.', '_').replace('-', '_').lower()
        
        # First try exact model ID match
        template_path = os.path.join(CONFIG_DIR, f"prompt_{clean_model_id}.txt")
        
        if not os.path.exists(template_path):
            # Try to find a generic template for the model family
            if "gpt2" in model_id.lower():
                template_path = os.path.join(CONFIG_DIR, "prompt_gpt2.txt")
            elif "llama" in model_id.lower():
                template_path = os.path.join(CONFIG_DIR, "prompt_llama.txt")
            else:
                # Default template
                template_path = os.path.join(CONFIG_DIR, "prompt_default.txt")
        
        try:
            if os.path.exists(template_path):
                with open(template_path, 'r') as f:
                    return f.read()
            else:
                logger.warning(f"Prompt template not found for {model_id} at {template_path}")
                return None
        except Exception as e:
            logger.error(f"Error loading prompt template for {model_id}: {e}")
            return None

    def create_prompt(command: str, model_id: str) -> str:
        """Create a prompt for the model to convert a command to JSON."""
        # Get the appropriate template for the model
        template = load_prompt_template(model_id)
        
        # Get validation context
        devices = VALIDATION_CONFIG.get("devices", [])
        locations = VALIDATION_CONFIG.get("locations", [])
        actions = VALIDATION_CONFIG.get("actions", [])
        
        # Build validation context
        validation_context = f"""
Available devices: {', '.join(devices)}
Available locations: {', '.join(locations)}
Available actions: {', '.join(actions)}

Location synonyms:
"""
        # Add location synonyms
        for syn_name, syn_locations in VALIDATION_CONFIG.get("synonyms", {}).get("locations", {}).items():
            if isinstance(syn_locations, list):
                validation_context += f"- {syn_name}: {', '.join(syn_locations)}\n"
        
        # Add device synonyms
        validation_context += "\nDevice synonyms:\n"
        for device, syns in VALIDATION_CONFIG.get("synonyms", {}).get("devices", {}).items():
            if isinstance(syns, list):
                validation_context += f"- {device}: {', '.join(syns)}\n"
        
        if not template:
            # If no template is found, use a minimal fallback with validation context
            return f'''Convert this command to JSON: "{command}"

{validation_context}

Output format:
{{"device": string, "location": string | null, "action": string, "value": string | null}}

Note: Only use devices, locations, and actions from the lists above.'''
        
        # Escape any quotes in the command to prevent format string issues
        escaped_command = command.replace('"', '\\"')
        
        try:
            # Add validation context to the template
            return template.format(
                command=escaped_command,
                validation_context=validation_context
            )
        except Exception as e:
            logger.error(f"Error formatting prompt template: {e}")
            # Use minimal fallback if formatting fails
            return f'''Convert this command to JSON: "{escaped_command}"

{validation_context}

Output format:
{{"device": string, "location": string | null, "action": string, "value": string | null}}

Note: Only use devices, locations, and actions from the lists above.'''

    def process_command(raw_text: str) -> dict:
        """Extract JSON from model output."""
        try:
            # Try to find JSON-like content using regex
            import re
            json_pattern = r'\{(?:[^{}]|(?:\{[^{}]*\}))*\}'
            matches = re.findall(json_pattern, raw_text)
            
            if not matches:
                logging.warning("No JSON-like content found in response")
                return None
                
            # Find the longest match which is most likely to be our full JSON object
            best_match = max(matches, key=len)
            
            # Parse and validate JSON
            result = json.loads(best_match)
            
            # Ensure the required fields are present
            required_fields = ["device", "location", "action", "value"]
            for field in required_fields:
                if field not in result:
                    logging.warning(f"Missing required field: {field}")
                    result[field] = None
                    
            # Validate the command
            validation_error = validate_command(result)
            if validation_error:
                logging.warning(f"Validation error: {validation_error}")
                return None
                
            return result
            
        except json.JSONDecodeError as e:
            logging.error(f"JSON decode error: {e}")
            return None
        except Exception as e:
            logging.error(f"Error processing command: {e}")
            return None

# ---------------- Logging & device -----------------
logging.basicConfig(level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("/app/logs/voice_service.log")])
logger = logging.getLogger("voice-service")
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
logger.info(f"Using device: {DEVICE}")
if DEVICE == "cuda":
    try:
        gprop = torch.cuda.get_device_properties(0)
        logger.info(f"GPU: {gprop.name} | {gprop.total_memory/1e9:.2f} GB")
    except Exception as e:
        logger.warning(f"GPU info retrieval failed: {e}")

# ---------------- Paths ----------------------------
MODELS_DIR = os.environ.get("MODELS_DIR", "/models")
CONFIG_DIR = os.environ.get("CONFIG_DIR", "/app/config")
os.makedirs(MODELS_DIR, exist_ok=True)
os.makedirs(CONFIG_DIR, exist_ok=True)

# ---------------- Model aliases --------------------
MODEL_ALIASES: dict[str, str] = {
    "tinyllama": "TinyLlama/TinyLlama-1.1B-Chat-v1.0",
    "pythia": "EleutherAI/pythia-70m",
    "phi2": "microsoft/phi-2",
    "mistral": "nilq/mistral-1L-tiny",
    "qwen": "Qwen/Qwen1.5-0.5B-Chat",
    "qwen3-1.7b": "Qwen/Qwen3-1.7B",
    "qwen3-0.6b": "Qwen/Qwen3-0.6B",
    "qwen3-0.6b-fp8": "Qwen/Qwen3-0.6B-FP8",
    # GGUF model aliases
    "qwen3-0.6b-gguf": "Qwen3-0.6B-Q4_K_M.gguf",
    "qwen3-1.7b-gguf": "Qwen3-1.7B-Q4_K_M.gguf"
}
RECOMMENDED_MODELS = [
    "tinyllama", "qwen3-0.6b", "qwen3-0.6b-fp8", "qwen3-1.7b", 
    "qwen3-0.6b-gguf", "qwen3-1.7b-gguf",  # Add GGUF models to recommended list
    "distilgpt2", "gpt2"
]

# ---------------- State ----------------------------
loaded_models: Dict[str, Dict[str, Any]] = {}
current_model_id: Optional[str] = None
model_lock = Lock()
start_time = time.time()

# ---------------- Helper: HF cache dir -------------

def model_id_to_dir_name(mid: str) -> str:
    return "models--" + "--".join(mid.split("/"))

def dir_name_to_model_id(dname: str) -> str:
    return "/".join(dname[len("models--"):].split("--")) if dname.startswith("models--") else dname

def list_available_models() -> List[str]:
    cache = os.path.join(MODELS_DIR, "cache")
    if not os.path.isdir(cache):
        return []
    return [dir_name_to_model_id(d) for d in os.listdir(cache) if d.startswith("models--")]

# ---------------- Pydantic models ------------------
class QueryRequest(BaseModel):
    prompt: str
    model_id: Optional[str] = Field(None, description="ID or alias")
    temperature: float = Field(0.7, ge=0.0, le=1.0)
    max_tokens: int = Field(150, ge=1, le=2048)
    class Config: protected_namespaces = ()

class QueryResponse(BaseModel):
    command: Optional[Dict[str, Any]] = None
    raw_generation: str = ""
    model_used: str = ""
    error: Optional[str] = None
    class Config: protected_namespaces = ()

class ModelInfo(BaseModel):
    model_id: str; is_loaded: bool; is_current: bool = False; model_type: str = ""
    class Config: protected_namespaces = ()

# ---------------- Model configs --------------------
def load_configs() -> tuple[Dict[str, Dict[str, Any]], Dict[str, Any]]:
    """Load model-specific configurations and validation rules from YAML files."""
    model_config_path = os.path.join(CONFIG_DIR, "model_configs.yaml")
    validation_path = os.path.join(CONFIG_DIR, "validation.yaml")
    
    model_configs = {}
    validation_config = {}
    
    try:
        if os.path.exists(model_config_path):
            with open(model_config_path, 'r') as f:
                model_configs = yaml.safe_load(f) or {}
        else:
            logger.warning(f"Model config file not found at {model_config_path}")
            
        if os.path.exists(validation_path):
            with open(validation_path, 'r') as f:
                validation_config = yaml.safe_load(f) or {}
        else:
            logger.warning(f"Validation config file not found at {validation_path}")
            
    except Exception as e:
        logger.error(f"Error loading configs: {e}")
    
    return model_configs, validation_config

MODEL_CONFIGS, VALIDATION_CONFIG = load_configs()

def validate_command(cmd: Dict[str, Any]) -> Optional[str]:
    """Validate a command against the validation rules."""
    if not cmd:
        return "No command provided"
        
    # Validate device
    if cmd.get("device") not in VALIDATION_CONFIG.get("devices", []):
        return f"Invalid device: {cmd.get('device')}"
        
    # Validate location if provided
    if cmd.get("location"):
        valid_locations = VALIDATION_CONFIG.get("locations", [])
        # Check synonyms
        for syn_group in VALIDATION_CONFIG.get("synonyms", {}).get("locations", {}).values():
            if isinstance(syn_group, list) and cmd["location"] in syn_group:
                return None
        if cmd["location"] not in valid_locations:
            return f"Invalid location: {cmd.get('location')}"
            
    # Validate action
    if cmd.get("action") not in VALIDATION_CONFIG.get("actions", []):
        return f"Invalid action: {cmd.get('action')}"
        
    return None

def process_command(raw_text: str) -> dict:
    """Extract JSON from model output."""
    try:
        # Try to find JSON-like content using regex
        import re
        json_pattern = r'\{(?:[^{}]|(?:\{[^{}]*\}))*\}'
        matches = re.findall(json_pattern, raw_text)
        
        if not matches:
            logging.warning("No JSON-like content found in response")
            return None
            
        # Find the longest match which is most likely to be our full JSON object
        best_match = max(matches, key=len)
        
        # Parse and validate JSON
        result = json.loads(best_match)
        
        # Ensure the required fields are present
        required_fields = ["device", "location", "action", "value"]
        for field in required_fields:
            if field not in result:
                logging.warning(f"Missing required field: {field}")
                result[field] = None
                
        # Validate the command
        validation_error = validate_command(result)
        if validation_error:
            logging.warning(f"Validation error: {validation_error}")
            return None
                
        return result
        
    except json.JSONDecodeError as e:
        logging.error(f"JSON decode error: {e}")
        return None
    except Exception as e:
        logging.error(f"Error processing command: {e}")
        return None

# ---------------- GGUF Support --------------------
class ModelLoader:
    """Handles loading of both Hugging Face and GGUF models."""
    
    def __init__(self, models_dir: str):
        self.models_dir = models_dir
        self.gguf_dir = os.path.join(models_dir, "gguf")
        os.makedirs(self.gguf_dir, exist_ok=True)
    
    def is_gguf_model(self, model_id: str) -> bool:
        """Check if the model is a GGUF model."""
        return model_id.endswith('.gguf') or os.path.exists(os.path.join(self.gguf_dir, model_id))
    
    def get_gguf_path(self, model_id: str) -> str:
        """Get the full path to a GGUF model file."""
        if model_id.endswith('.gguf'):
            return os.path.join(self.gguf_dir, model_id)
        return os.path.join(self.gguf_dir, f"{model_id}.gguf")
    
    def load_gguf_model(self, model_id: str) -> tuple[Any, Any]:
        """Load a GGUF model and create a compatible tokenizer."""
        if not GGUF_AVAILABLE:
            raise ImportError("llama-cpp-python not installed")
            
        model_path = self.get_gguf_path(model_id)
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"GGUF model not found: {model_path}")
            
        # Get model-specific config
        config = MODEL_CONFIGS.get(model_id, {})
        
        # Load the GGUF model with configuration
        model = Llama(
            model_path=model_path,
            n_ctx=config.get("n_ctx", 2048),
            n_threads=config.get("n_threads", 4),
            n_gpu_layers=config.get("n_gpu_layers", 0),
            n_batch=config.get("n_batch", 512),
            verbose=False
        )
        
        # Create a simple tokenizer interface
        class GGUFTokenizer:
            def __init__(self, model):
                self.model = model
                self.model_max_length = config.get("n_ctx", 2048)
                self.pad_token = "</s>"
                self.eos_token = "</s>"
                self.pad_token_id = 0
                self.eos_token_id = 0
            
            def __call__(self, text, **kwargs):
                # Convert input to tokens
                tokens = self.model.tokenize(text.encode())
                return {"input_ids": torch.tensor([tokens])}
            
            def decode(self, tokens, **kwargs):
                # Convert tokens back to text
                return self.model.detokenize(tokens).decode()
        
        tokenizer = GGUFTokenizer(model)
        return model, tokenizer
    
    def load_hf_model(self, model_id: str) -> tuple[Any, Any]:
        """Load a Hugging Face model with quantization."""
        cache = os.path.join(self.models_dir, "cache")
        t_kwargs = {"trust_remote_code": True, "cache_dir": cache}
        tokenizer = AutoTokenizer.from_pretrained(model_id, **t_kwargs)
        
        # Handle pad token
        if tokenizer.pad_token is None:
            if tokenizer.eos_token:
                tokenizer.pad_token = tokenizer.eos_token
            else:
                tokenizer.add_special_tokens({"pad_token": "[PAD]"})
                tokenizer.pad_token = "[PAD]"
        
        # Load model with quantization
        m_kwargs = {"trust_remote_code": True, "cache_dir": cache}
        if DEVICE == "cuda":
            m_kwargs.update({
                "device_map": "auto",
                "torch_dtype": torch.float16,
                "low_cpu_mem_usage": True
            })
        
        model = AutoModelForCausalLM.from_pretrained(model_id, **m_kwargs)
        
        # Resize token embeddings if needed
        if model.config.vocab_size < len(tokenizer):
            model.resize_token_embeddings(len(tokenizer))
            
        return model, tokenizer

# Initialize model loader
model_loader = ModelLoader(MODELS_DIR)

# ---------------- Model lifecycle ------------------
async def unload_model(mid: str) -> bool:
    global current_model_id
    fid = MODEL_ALIASES.get(mid.lower(), mid)
    async with model_lock:
        if fid not in loaded_models:
            return False
            
        bundle = loaded_models.pop(fid)
        try:
            # Check if it's a GGUF model
            if isinstance(bundle["model"], Llama):
                # GGUF models need explicit cleanup
                bundle["model"].free()
            else:
                # Hugging Face models
                bundle["model"].to("cpu")
                bundle["model"].cpu()
                
            # Clear tokenizer
            if hasattr(bundle["tokenizer"], "model"):
                bundle["tokenizer"].model = None
                
            # Delete the bundle
            del bundle
            
            # Force garbage collection
            gc.collect()
            
            # Clear CUDA cache if available
            if DEVICE == "cuda":
                torch.cuda.empty_cache()
                torch.cuda.synchronize()
                
            # Reset current model if needed
            if current_model_id == fid:
                current_model_id = None
                
            logger.info(f"Successfully unloaded model: {fid}")
            return True
            
        except Exception as e:
            logger.error(f"Error unloading model {fid}: {e}")
            return False

async def load_model(mid: str) -> None:
    global current_model_id
    fid = MODEL_ALIASES.get(mid.lower(), mid)
    async with model_lock:
        if fid in loaded_models:
            current_model_id = fid
            return
        if current_model_id:
            await unload_model(current_model_id)
        
        try:
            if model_loader.is_gguf_model(fid):
                model, tokenizer = model_loader.load_gguf_model(fid)
            else:
                model, tokenizer = model_loader.load_hf_model(fid)
                
            loaded_models[fid] = {"model": model, "tokenizer": tokenizer, "loaded_at": datetime.utcnow()}
            current_model_id = fid
            
        except Exception as e:
            logger.error(f"Error loading model {fid}: {e}")
            raise

# ---------------- Generation helper ----------------
async def generate_raw(model, tokenizer, prompt: str, temp: float, mx: int) -> str:
    try:
        # Get model-specific config
        model_id = next((mid for mid, bundle in loaded_models.items() if bundle["model"] is model), None)
        config = MODEL_CONFIGS.get(model_id, {})
        
        # Handle potential tokenizer overflow by ensuring max_length is within safe bounds
        max_length = min(tokenizer.model_max_length, 2048)
        
        # Check if this is a GGUF model
        is_gguf = isinstance(model, Llama)
        
        if is_gguf:
            # GGUF model generation
            response = model(
                prompt,
                max_tokens=mx,
                temperature=config.get("temperature", temp),
                stop=["</s>", "}"],  # Stop at end of sentence or JSON
                echo=False  # Don't include the prompt in the output
            )
            return response["choices"][0]["text"]
        else:
            # Hugging Face model generation
            enc = tokenizer(
                prompt, 
                return_tensors="pt", 
                padding=True, 
                truncation=True, 
                max_length=max_length,
                return_token_type_ids=config.get("return_token_type_ids", True)
            )
            
            # Move inputs to device
            inp = {k: v.to(DEVICE) for k, v in enc.items()}
            
            # Generate with model-specific parameters
            with torch.no_grad():
                out = model.generate(
                    **inp,
                    max_new_tokens=mx,
                    temperature=config.get("temperature", temp),
                    do_sample=config.get("do_sample", True),
                    pad_token_id=tokenizer.eos_token_id
                )
                
            return tokenizer.decode(out[0], skip_special_tokens=True)
    
    except Exception as e:
        logger.error(f"Generation error: {e}")
        return f"Error: Could not generate response: {str(e)}"

# ---------------- FastAPI --------------------------
app = FastAPI(title="Voice Service – Smart Home Control")

@app.post("/smart-home/command", response_model=QueryResponse)
async def cmd(req: QueryRequest, _: BackgroundTasks):
    if not req.model_id and not current_model_id:
        for cand in RECOMMENDED_MODELS:
            try: await load_model(cand); break
            except Exception: continue
    if req.model_id: await load_model(req.model_id)
    if not current_model_id: raise HTTPException(500, "No model available")
    b = loaded_models[current_model_id]
    prompt = create_prompt(req.prompt, current_model_id)
    raw = await generate_raw(b["model"], b["tokenizer"], prompt, req.temperature, req.max_tokens)
    try:
        cmd_json = process_command(raw); err = None if cmd_json else "No JSON command found"
    except Exception as e:
        cmd_json, err = None, f"Parsing error: {e}"
    return QueryResponse(command=cmd_json, raw_generation=raw, model_used=current_model_id, error=err)

@app.get("/models", response_model=List[ModelInfo])
async def models():
    infos = [ModelInfo(model_id=m, is_loaded=True, is_current=(m==current_model_id)) for m in loaded_models]
    seen = {i.model_id for i in infos}
    for m in list_available_models():
        if m not in seen: infos.append(ModelInfo(model_id=m, is_loaded=False)); seen.add(m)
    for alias, full in MODEL_ALIASES.items():
        if full in seen and alias not in seen: infos.append(ModelInfo(model_id=alias, is_loaded=False, model_type="alias"))
    for rec in RECOMMENDED_MODELS:
        if rec not in seen: infos.append(ModelInfo(model_id=rec, is_loaded=False, model_type="recommended"))
    return sorted(infos, key=lambda x: (not x.is_loaded, x.model_id))

@app.get("/load-model")
async def load_get(model_id: str): await load_model(model_id); return {"status":"success","message":f"Loaded {model_id}"}

@app.get("/unload-model")
async def unload_get(model_id: str): return {"status":"success" if await unload_model(model_id) else "skipped","message":f"Unloaded {model_id}"}

@app.get("/memory")
async def memory():
    vm = psutil.virtual_memory()
    info = {"total_ram": vm.total/2**30, "available_ram": vm.available/2**30, "used_ram": vm.used/2**30, "ram_percent": vm.percent}
    if DEVICE == "cuda":
        try:
            props = torch.cuda.get_device_properties(0)
            used = torch.cuda.memory_allocated()/2**30
            info.update({"total_gpu": props.total_memory/2**30, "used_gpu": used, "gpu_percent": used/(props.total_memory/2**30)*100})
        except Exception as e:
            logger.warning(f"GPU mem query failed: {e}")
    return info

@app.get("/health")
async def health():
    return {"status":"healthy","device":DEVICE,"current_model":current_model_id,"loaded":list(loaded_models)}

# ---------------- Root (plain + html) --------------
@app.get("/", response_class=HTMLResponse)
async def root(req: Request):
    infos = await models()
    rows = [(i.model_id,"LOADED" if i.is_loaded else "…", i.model_type) for i in infos]
    uptime = int(time.time()-start_time)
    libs = {lib: pkg_resources.get_distribution(lib).version for lib in ["fastapi","uvicorn","torch","transformers","psutil"]}
    mem = await memory()
    accept=req.headers.get("accept","text/plain")
    if "text/html" not in accept:
        width=max(len(r[0]) for r in rows) if rows else 10
        txt="ORAC – Voice Service\n\nModels\n"+"ID".ljust(width)+" status type\n"+"-"*(width+14)+"\n"
        for r in rows: txt+=f"{r[0].ljust(width)} {r[1]:>6} {r[2]}\n"
        txt+="\nUptime: "+str(uptime)+"s\nRAM used: {:.1f}%".format(mem['ram_percent'])
        return PlainTextResponse(txt)
    # --- HTML ---
    html="""<html><head><title>ORAC</title>
    <style>
        body { font-family: sans-serif; margin: 20px; }
        table { border-collapse: collapse; margin-bottom: 20px; }
        th, td { border: 1px solid #ddd; padding: 6px; }
        .prompt-section { margin: 20px 0; }
        .prompt-input { width: 100%; padding: 8px; margin: 10px 0; }
        .response-section { margin: 20px 0; }
        .json-response { 
            background: #f5f5f5; 
            padding: 10px; 
            border-radius: 4px;
            font-family: monospace;
            white-space: pre-wrap;
        }
        .json-highlight { 
            color: #0066cc; 
            font-weight: bold; 
        }
        button { 
            padding: 6px 12px; 
            margin: 0 4px;
            cursor: pointer;
        }
        button:disabled { 
            opacity: 0.5; 
            cursor: not-allowed;
        }
        #msg { 
            margin-top: 10px; 
            font-weight: bold; 
        }
        .loading { 
            opacity: 0.5; 
            pointer-events: none; 
        }
            </style>
        </head>
        <body>
    <h2>ORAC – Voice Service</h2>
    
    <div class="prompt-section">
        <h3>Test Prompt</h3>
        <textarea id="prompt" class="prompt-input" rows="3" placeholder="Enter your command here..."></textarea>
        <button onclick="submitPrompt()" id="submitBtn">Submit</button>
    </div>
    
    <div class="response-section" id="responseSection" style="display: none;">
        <h3>Response</h3>
        <div id="rawResponse" class="json-response"></div>
        <div id="jsonResponse" class="json-response"></div>
    </div>
    
            <h3>Available Models</h3>
            <table>
        <tr><th>ID</th><th>Status</th><th>Type</th><th>Action</th></tr>"""
    
    for mid,st,tp in rows:
        loaded=st=="LOADED"
        html+=f"<tr><td>{mid}</td><td>{st}</td><td>{tp}</td><td><button onclick=\"act(this,'{mid}','load')\" {'disabled' if loaded else ''}>Load</button><button onclick=\"act(this,'{mid}','unload')\" {'disabled' if not loaded else ''}>Unload</button></td></tr>"
    
    html += """
            </table>
    <div id='msg' style='margin-top:10px;font-weight:bold;'></div>
    
    <script>
    function flash(msg, ok) {
        const m = document.getElementById('msg');
        m.textContent = msg;
        m.style.color = ok ? '#3c763d' : '#a94442';
    }
    
    async function act(btn,id,action){
        const orig=btn.textContent;
        btn.disabled=true;
        btn.textContent = action==='load' ? 'Loading…' : 'Unloading…';
        try{
            const res = await fetch(`/${action}-model?model_id=`+encodeURIComponent(id));
            const data = await res.json();
            flash(data.message, res.ok);
        }catch(e){
            flash(e.message,false);
        }
        setTimeout(()=>location.reload(),800);
    }
    
    async function submitPrompt() {
        const prompt = document.getElementById('prompt').value;
        if (!prompt) return;
        
        const submitBtn = document.getElementById('submitBtn');
        const responseSection = document.getElementById('responseSection');
        const rawResponse = document.getElementById('rawResponse');
        const jsonResponse = document.getElementById('jsonResponse');
        
        submitBtn.disabled = true;
        submitBtn.textContent = 'Processing...';
        responseSection.style.display = 'none';
        
        try {
            const res = await fetch('/smart-home/command', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ prompt: prompt })
            });
            const data = await res.json();
            
            // Display raw response
            rawResponse.textContent = data.raw_generation;
            
            // Display JSON response if available
            if (data.command) {
                jsonResponse.innerHTML = '<span class="json-highlight">' + 
                    JSON.stringify(data.command, null, 2) + '</span>';
            } else {
                jsonResponse.textContent = 'No JSON command found';
            }
            
            responseSection.style.display = 'block';
            flash(data.error || 'Success', !data.error);
        } catch (e) {
            flash(e.message, false);
        } finally {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Submit';
        }
    }
    </script>
    </body></html>"""
    return HTMLResponse(html)

# ---------------- Entrypoint -----------------------
if __name__=="__main__":
    logger.info("Starting server on 0.0.0.0:8000 …")
    uvicorn.run(app, host="0.0.0.0", port=8000)