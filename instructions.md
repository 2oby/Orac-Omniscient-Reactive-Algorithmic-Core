TODO NEXT:
ORAC Project Code Changes and Improvements
Based on the issues identified in the test logs and code analysis, here are recommended changes to fix the async coroutine issues and improve the overall functionality:
1. Fix Test Files to Properly Handle Async Functions
The primary issue appears to be in the test files where async functions aren't being properly awaited.
python# Current problematic code in tests/test_model_management.py
client.load_model("nonexistent-model")  # Not awaited
client.unload_model("test-model")       # Not awaited

# Fix by properly awaiting coroutines
await client.load_model("nonexistent-model")
await client.unload_model("test-model")
Implementation:

Ensure all test functions that call async methods are defined with async def
Add @pytest.mark.asyncio decorator to these test functions
Use await when calling any async function

2. Add Explicit PyTest AsyncIO Configuration
Add configuration for pytest-asyncio to fix the warning about undefined asyncio loop scope.
python# Add to pytest.ini or conftest.py
[pytest]
asyncio_mode = auto
asyncio_default_fixture_loop_scope = function
3. Update OllamaClient to Improve Error Handling
Enhance error handling in the OllamaClient class to provide more descriptive errors.
python# In ollama_client.py, update the load_model method
async def load_model(self, name: str, max_retries: int = 3) -> ModelLoadResponse:
    """Load a model by name."""
    try:
        result = await self.model_loader.load_model(name, max_retries)
        return ModelLoadResponse(status=result["status"])
    except ModelLoader.ModelError as e:
        # Add detailed logging
        print(f"Model loading error: {e.stage} - {e.message}")
        raise Exception(f"Failed to load model at stage {e.stage}: {e.message}")
    except Exception as e:
        raise Exception(f"Failed to load model: {str(e)}")
4. Add Validation for Model Existence Before Loading
Add explicit validation to check if the model file exists before attempting to load it.
python# Add to model_loader.py, inside load_model method
model_path = self.resolve_model_path(name)
if not os.path.exists(model_path):
    self._log_error(f"Model file not found: {model_path}")
    raise self.ModelError(f"Model file not found: {model_path}", "validation")
5. Improve Model Path Resolution Logic
Update the model path resolution logic to better handle model discovery:
python# In model_loader.py, update resolve_model_path
def resolve_model_path(self, name: str) -> str:
    """Resolve the full path to a model file."""
    # Try environment variable first
    model_base_path = os.getenv("OLLAMA_MODEL_PATH", os.getenv("OLLAMA_MODELS"))
    
    if not model_base_path:
        # Fallback to default paths with more extensive checking
        default_paths = [
            "/models/gguf",          # Docker default
            "/app/models/gguf",      # App-relative path
            os.path.expanduser("~/models/gguf"),  # User home
            os.path.join(os.getcwd(), "models", "gguf"),  # Current directory
            os.path.join(os.path.dirname(os.getcwd()), "models", "gguf")  # Parent directory
        ]
        
        for path in default_paths:
            if os.path.exists(path):
                model_base_path = path
                break
    
    # Ensure the .gguf extension is present
    if not name.endswith(".gguf"):
        name = f"{name}.gguf"
    
    model_path = os.path.join(model_base_path, name)
    
    # Add detailed debug logging
    self._log_debug("model_path_resolved", {
        "base_path": model_base_path,
        "model_name": name,
        "full_path": model_path,
        "exists": os.path.exists(model_path),
        "docker_env": os.getenv("OLLAMA_MODELS", "not_set")
    })
    
    return model_path
6. Add Model Status Verification
Add an explicit function to verify model status after loading:
python# Add to model_loader.py
async def verify_model_status(self, model_name: str) -> bool:
    """Verify that a model is properly loaded and ready."""
    try:
        # Check if model appears in the list of loaded models
        response = await self.client.get("/api/tags")
        if response.status_code == 200:
            models = response.json().get("models", [])
            if any(m.get("name") == model_name for m in models):
                # Verify the model can process a simple prompt
                test_response = await self.client.post(
                    "/api/generate",
                    json={"model": model_name, "prompt": "test", "stream": False}
                )
                if test_response.status_code == 200:
                    self._log_debug("model_verification", {
                        "status": "success",
                        "model_name": model_name
                    })
                    return True
                
        self._log_error(f"Model verification failed for {model_name}")
        return False
    except Exception as e:
        self._log_error(f"Error verifying model {model_name}: {str(e)}")
        return False
7. Update Docker Compose Volume Mappings
Ensure the volume mappings in docker-compose.yml are correctly configured:
yamlvolumes:
  - ./models/gguf:/models/gguf:ro  # Host path:Container path:read-only
8. Implement Progress Tracking for Model Loading
Add progress tracking for model loading to provide better feedback:
python# In model_loader.py, update load_model
async def load_model(self, name: str, max_retries: int = MAX_MODEL_LOAD_RETRIES) -> dict:
    """Load a model into Ollama with progress tracking."""
    start_time = time.time()
    self._start_time = start_time
    model_name = self._sanitize_tag(name)
    
    self._log_debug("model_load_started", {
        "model_name": model_name,
        "start_time": start_time
    })
    
    # Check model paths with detailed logging
    model_path = self.resolve_model_path(name)
    
    # Add progress tracking to the create call
    payload = {
        "name": model_name,
        "from": model_path,
        "stream": True  # Switch to streaming for progress
    }
    
    try:
        # Stream the create response to track progress
        async with self.client.stream("POST", "/api/create", json=payload) as response:
            response.raise_for_status()
            
            async for line in response.aiter_lines():
                if line:
                    try:
                        data = json.loads(line)
                        # Log progress
                        if "progress" in data:
                            self._log_debug("model_load_progress", {
                                "model_name": model_name,
                                "progress": data["progress"],
                                "elapsed_time": time.time() - start_time
                            })
                        # Check for completion
                        if data.get("status") == "success":
                            self._log_debug("model_load_success", {
                                "model_name": model_name,
                                "elapsed_time": time.time() - start_time
                            })
                            return {"status": "success"}
                    except json.JSONDecodeError:
                        continue
    except Exception as e:
        self._log_error(f"Model load failed: {str(e)}")
        raise self.ModelError(str(e), "create")
    
    # Verify model is ready
    if await self.wait_for_model(model_name):
        return {"status": "success"}
    
    raise self.ModelError("Failed to load model within timeout", "verification")
9. Add Diagnostic Command-Line Tool
Create a diagnostic script to check model loading issues:
python# scripts/diagnose_model_loading.py
import asyncio
import os
import sys
from orac.model_loader import ModelLoader
import httpx

async def diagnose_model_loading(model_name):
    """Diagnose model loading issues."""
    print(f"Diagnosing model loading for: {model_name}")
    
    # Check environment variables
    print("\nEnvironment variables:")
    print(f"OLLAMA_HOST: {os.getenv('OLLAMA_HOST', 'not set')}")
    print(f"OLLAMA_PORT: {os.getenv('OLLAMA_PORT', 'not set')}")
    print(f"OLLAMA_MODEL_PATH: {os.getenv('OLLAMA_MODEL_PATH', 'not set')}")
    print(f"OLLAMA_MODELS: {os.getenv('OLLAMA_MODELS', 'not set')}")
    
    # Check if Ollama is running
    base_url = f"http://{os.getenv('OLLAMA_HOST', '127.0.0.1')}:{os.getenv('OLLAMA_PORT', '11434')}"
    print(f"\nChecking Ollama at: {base_url}")
    
    async with httpx.AsyncClient(base_url=base_url) as client:
        try:
            response = await client.get("/api/version")
            version = response.json().get("version", "unknown")
            print(f"Ollama version: {version}")
        except Exception as e:
            print(f"Failed to connect to Ollama: {str(e)}")
            return
        
        # Create model loader
        loader = ModelLoader(client)
        
        # Check model path
        model_path = loader.resolve_model_path(model_name)
        print(f"\nModel path resolution:")
        print(f"Resolved path: {model_path}")
        print(f"File exists: {os.path.exists(model_path)}")
        if os.path.exists(model_path):
            print(f"File size: {os.path.getsize(model_path)} bytes")
            print(f"File permissions: {oct(os.stat(model_path).st_mode)[-3:]}")
        
        # Check existing models
        response = await client.get("/api/tags")
        if response.status_code == 200:
            models = response.json().get("models", [])
            print(f"\nExisting models ({len(models)}):")
            for model in models:
                print(f"- {model.get('name')}")
        
        # Try loading the model
        print(f"\nAttempting to load model: {model_name}")
        try:
            result = await loader.load_model(model_name)
            print(f"Load result: {result}")
        except Exception as e:
            print(f"Load failed: {str(e)}")
        
        # Print error logs
        print("\nError logs:")
        for log in loader.get_error_logs():
            print(f"- {log}")

if __name__ == "__main__":
    model_name = sys.argv[1] if len(sys.argv) > 1 else "Qwen3-1.7B-Q4_K_M.gguf"
    asyncio.run(diagnose_model_loading(model_name))
Testing Strategy

Unit Tests:

Update existing tests to properly await async functions
Add tests for model path resolution with different environment configurations
Add tests for model file validation


Integration Tests:

Test the full model loading pipeline with a small test model
Verify error handling with non-existent models
Test unloading of models


Manual Testing:

Run the diagnostic script to verify model discovery and loading
Test with different environment variables
Verify model loading with streaming progress reports



Implementation Plan

Fix the async test issues first
Add the diagnostic script to help identify potential issues
Update the model path resolution logic
Implement the model verification improvements
Add progress tracking for model loading
Update Docker configuration if needed
Run the full test suite to verify fixes

Once these changes are implemented, the ORAC system should be able to properly load and manage models, with better error reporting and diagnostics to help identify any remaining issues.









# ORAC (MVP) — Authoring Guide for the Implementation LLM
*Jetson Orin Nano 8 GB — JetPack 6.0 (L4T r36.4.3) — CUDA 12.6*

---

## 0 · Purpose of This Guide
You (the implementation‑LLM) will build **ORAC**, a single‑container application that:

1. Runs multiple **GGUF** LLMs locally via **Ollama** (Qwen3‑0.6B/1.7B, TinyLlama‑1.1B, Pythia‑70M, DistilGPT‑2, Phi‑2).  
2. Exposes **one** external interface — a **FastAPI** REST service (port `8000`) that also serves a small web dashboard.  
3. Provides endpoints to list, load, unload, prompt, and benchmark the models.  
4. Records latency for each model in the benchmark.  

You must **code in small increments**.  
After *every* increment, write a minimal **test case** (unit or integration) that proves the new code works.

---

## 1 · Environment & Constraints
| Item | Value |
|------|-------|
| Base Docker image | `dustynv/ollama:r36.4.3` |
| Host GGUF folder  | `/home/toby/ORAC/models/gguf` (mounted read‑only at `/models/gguf` in the container) |
| External port     | `8000` (mapped host→container) |
| Internal Ollama port | `11434` (not exposed) |

> **Open question (flag for human review):**  
> If `dustynv/ollama:r36.4.3` ever lags behind Qwen 3 support, we may need to re‑build Ollama from source. Keep Dockerfile comments that show how to swap in a source‑build stage.

---

## 2 · High‑Level Directory Layout (inside container)

```
/app
├── orac/                 # Python package
│   ├── __init__.py
│   ├── config.py
│   ├── api.py            # FastAPI router
│   ├── ollama_client.py  # thin wrapper around localhost:11434
│   ├── models.py         # Pydantic models / schemas
│   ├── benchmark.py
│   └── web/              # index.html + small JS
├── tests/                # pytest tests
├── Dockerfile
└── requirements.txt
```

---

## 3 · Incremental Build Plan  

For **each step**, do **both**:

1. **Write the code** (only what's listed).  
2. **Add a test** proving the new piece works (`pytest` recommended).  

### Step 3.1 — Bootstrap the repo  
*Goal*: skeleton project & passing "sanity" test.  

*Tasks for you*  
- Create the directory tree above.  
- Add a minimal `__init__.py`.  
- Fill `requirements.txt` with:  
  ```text
  fastapi
  uvicorn[standard]
  pydantic
  httpx
  pytest
  ```

Test: pytest -q succeeds (zero tests).

### Step 3.2 — Dockerfile & Compose
*Goal*: container builds and starts FastAPI "hello".

*Tasks*
- Write Dockerfile that:
  - starts from dustynv/ollama:r36.4.3,
  - installs Python 3.10 + pip if missing,
  - copies /app, installs requirements.txt,
  - sets ENV OLLAMA_MODELS=/models/gguf,
  - exposes 8000,
  - ENTRYPOINT [ "uvicorn", "orac.api:app", "--host", "0.0.0.0", "--port", "8000" ].
- (Optional) add docker-compose.yml mapping host port 8000:8000 and volume /home/toby/ORAC/models/gguf:/models/gguf:ro.

Test: a script that builds the image and asserts curl http://localhost:8000/docs returns 200.

### Step 3.3 — Ollama client wrapper
*Goal*: minimal POST to /api/tags and /api/generate.

*Tasks*
- Implement ollama_client.py with async list_models(), generate(model, prompt), pull(model), show(model), delete(model).
- Use internal base URL http://127.0.0.1:11434.

Test: mock Ollama with respx or similar; verify list_models() parses response.

### Step 3.4 — FastAPI "model list" endpoint
*Goal*: /v1/models proxy to Ollama.

*Tasks*
- Define Pydantic ModelInfo.
- Route GET /v1/models returns list of available models.

Test: mock ollama_client.list_models().

### Step 3.5 — Load / Unload endpoints
*Goal*:
- POST /v1/models/{name}/load
- POST /v1/models/{name}/unload

*Tasks*
- Route calls ollama_client.pull() / delete().
- Return JSON status.

Test: simulate pulling TinyLlama from local GGUF path.

### Step 3.6 — Prompt endpoint
*Goal*: POST /v1/prompt with body { "model": "tinyllama:latest", "prompt": "Hello" }.

*Tasks*
- Stream or full‑buffer response from Ollama, return { "response": "…" , "elapsed_ms": N }.

Test: mock latency, assert timing field present.

### Step 3.7 — Benchmark endpoint
*Goal*: POST /v1/benchmark returns per‑model latency & answer.

*Tasks*
- Iterate over all loaded models (or accept explicit list).
- Aggregate results.

Test: monkey‑patch generate() to return within given ms; assert latencies sorted ascending.

### Step 3.8 — Web dashboard
*Goal*: serve / (index.html) that hits the API via fetch.

*Tasks*
- Place index.html & tiny JS in orac/web/; mount via StaticFiles.
- Provide UI: list models, buttons to load/unload, textarea to prompt, table with benchmark results.

Test: pytest that static route returns 200 and HTML contains <script>.

### Step 3.9 — Health endpoint
*Goal*: GET /v1/health returns versions, free RAM, GPU mem, CUDA, uptime.

*Tasks*
- Parse /proc/meminfo, call jetson_stats if available, fall back gracefully.

Test: assert required keys in JSON.

## 4 · Test Data & Models
You (implementation‑LLM) do not download models.
Assume GGUF files are already in /models/gguf.
For unit tests, mock Ollama or use a tiny dummy model to stay < 100 MB.

## 5 · Manual Script: safetensors → GGUF (optional)
Leave a commented‑out Python script (scripts/convert_safetensors.py) that calls llama.cpp/convert.py.
Not part of automated build; user runs it manually.

## 6 · Completion Criteria
docker build -t orac . succeeds on Jetson Orin Nano.

docker run --rm -p 8000:8000 -v /home/toby/ORAC/models/gguf:/models/gguf:ro orac
FastAPI docs available at http://jetson-ip:8000/docs.

POST /v1/models/{name}/load followed by POST /v1/prompt returns a valid response from each of the six target models.

POST /v1/benchmark returns latency numbers.

All pytest tests pass inside the container.

End of guide.