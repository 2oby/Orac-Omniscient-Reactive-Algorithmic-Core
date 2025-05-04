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