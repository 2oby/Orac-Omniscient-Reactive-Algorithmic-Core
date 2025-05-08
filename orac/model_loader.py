"""
orac.model_loader
----------------
Handles the core logic for loading models into Ollama, including:
- Version detection and schema selection
- Model path resolution and validation
- Modelfile generation
- Model loading and readiness verification

This module separates the model loading concerns from the client API wrapper,
making the code more maintainable and easier to test.
"""

import os
import json
import asyncio
import traceback
import tempfile
import re
from typing import Optional, Tuple, List, Dict
import httpx

class ModelLoader:
    def __init__(self, client: httpx.AsyncClient):
        self.client = client
        self._error_logs: List[str] = []
        self._debug_logs: List[Dict] = []

    def _log_error(self, message: str, context: Dict = None):
        """Add error message to logs with optional context."""
        log_entry = {"message": message}
        if context:
            # Filter out sensitive information from context
            safe_context = {}
            for key, value in context.items():
                if key in ["error", "status_code", "stage", "attempt"]:
                    safe_context[key] = value
                elif key == "response":
                    # Only include error message from response
                    if isinstance(value, str):
                        try:
                            resp_data = json.loads(value)
                            safe_context[key] = resp_data.get("error", "Unknown error")
                        except:
                            safe_context[key] = "Invalid JSON response"
                else:
                    safe_context[key] = value
            log_entry.update(safe_context)
        self._error_logs.append(json.dumps(log_entry))
        # Print the error immediately
        print(f"\n[ERROR] {message}")
        if context:
            for key, value in safe_context.items():
                print(f"  {key}: {value}")

    def _log_debug(self, stage: str, data: Dict):
        """Add debug information with stage and data."""
        log_entry = {
            "stage": stage,
            "timestamp": asyncio.get_event_loop().time(),
            "data": data
        }
        self._debug_logs.append(log_entry)
        # Print the log entry immediately
        print(f"\n[DEBUG] {stage}:")
        for key, value in data.items():
            print(f"  {key}: {value}")

    def get_error_logs(self) -> List[str]:
        """Get collected error logs."""
        return self._error_logs

    def get_debug_logs(self) -> List[Dict]:
        """Get collected debug logs."""
        return self._debug_logs

    async def get_ollama_version(self) -> Tuple[float, bool]:
        """Get Ollama version and determine if new schema should be used."""
        try:
            url = self.client.base_url.join("/api/version")
            print(f"[DEBUG] VERSION → {url}")
            response = await self.client.get("/api/version")
            body = await response.aread()
            print(f"[DEBUG] VERSION ← {response.status_code}, body={body!r}")
            response.raise_for_status()
            version = response.json().get("version", "0.0.0")
            
            version_parts = version.split('.')
            if len(version_parts) >= 2:
                major = int(version_parts[0])
                minor = int(version_parts[1])
                version_num = float(f"{major}.{minor}")
                return version_num, version_num >= 0.6
        except httpx.HTTPStatusError as e:
            raw = await e.response.aread()
            print(f"[ERROR] VERSION failed {e.response.status_code}: {raw!r}")
            self._log_error(f"Failed to get Ollama version: {str(e)}")
        except Exception as e:
            self._log_error(f"Failed to get Ollama version: {str(e)}")
        return 0.0, True  # Default to new schema on error

    def _sanitize_tag(self, name: str) -> str:
        """
        Sanitize model name to be compatible with Ollama 0.6.7+ requirements.
        - Remove .gguf extension
        - Convert to lowercase
        - Replace dots and underscores with hyphens
        - Remove any other special characters
        - Normalize multiple hyphens
        - Remove leading/trailing hyphens
        """
        # Remove .gguf extension and convert to lowercase
        base_name = name.removesuffix(".gguf").lower()
        
        # Replace dots and underscores with hyphens
        base_name = re.sub(r'[._]+', '-', base_name)
        
        # Remove any other special characters except alphanumeric and hyphens
        base_name = re.sub(r'[^a-z0-9-]', '', base_name)
        
        # Normalize multiple hyphens to single hyphen
        base_name = re.sub(r'-{2,}', '-', base_name)
        
        # Remove leading/trailing hyphens
        base_name = base_name.strip('-')
        
        # Handle tag specification (e.g., "model:tag")
        if ":" in base_name:
            model, tag = base_name.split(":", 1)
            return f"{model}:{tag}"
        
        return base_name

    def normalize_model_name(self, name: str) -> str:
        """Convert model name to valid Ollama tag format."""
        return self._sanitize_tag(name)

    def resolve_model_path(self, name: str) -> str:
        """Resolve the full path to a model file."""
        model_base_path = os.getenv("OLLAMA_MODEL_PATH", "/models/gguf")
        return os.path.join(model_base_path, name)

    def validate_model_file(self, path: str) -> None:
        """Validate that model file exists and is readable."""
        if not os.path.exists(path):
            raise FileNotFoundError(f"Model file not found at {path}")
        if not os.access(path, os.R_OK):
            raise PermissionError(f"Model file not readable at {path}")

    def create_modelfile(self, model_path: str, use_new_schema: bool) -> str:
        """Create appropriate Modelfile content based on schema version."""
        return f"FROM {model_path}\n"

    def write_modelfile_to_temp(self, modelfile_content: str) -> Tuple[str, bool]:
        """Write Modelfile content to a temporary file and return its path and whether it was created.
        
        Returns:
            Tuple[str, bool]: (path to modelfile, whether it was newly created)
        """
        # First check if a Modelfile already exists in the model directory
        model_dir = os.path.dirname(modelfile_content.split("FROM ")[1].strip())
        existing_modelfile = os.path.join(model_dir, "Modelfile")
        
        if os.path.exists(existing_modelfile):
            self._log_debug("using_existing_modelfile", {"path": existing_modelfile})
            return existing_modelfile, False
            
        # If no existing Modelfile, create a temporary one
        tf = tempfile.NamedTemporaryFile("w", delete=False, prefix="Modelfile_")
        try:
            tf.write(modelfile_content)
            tf.close()
            return tf.name, True
        except Exception as e:
            if tf:
                tf.close()
                try:
                    os.unlink(tf.name)
                except:
                    pass
            raise Exception(f"Failed to write Modelfile: {str(e)}")

    async def wait_for_model(self, model_name: str, max_retries: int = 30, delay: float = 2.0) -> bool:
        """Wait for a model to be ready."""
        for i in range(max_retries):
            try:
                response = await self.client.post("/api/show", json={"name": model_name})
                if response.status_code == 200:
                    return True
                
                response = await self.client.get("/api/tags")
                if response.status_code == 200:
                    models = response.json().get("models", [])
                    if any(model.get("name") == model_name for model in models):
                        return True
            except Exception as e:
                self._log_error(f"Error checking model status: {str(e)}")
            
            if i < max_retries - 1:
                await asyncio.sleep(delay)
        return False

    class ModelError(Exception):
        """Custom exception for model loading errors."""
        def __init__(self, message: str, stage: str, status_code: int = None):
            self.message = message
            self.stage = stage
            self.status_code = status_code
            super().__init__(f"{stage}: {message}")

    async def load_model(self, name: str, max_retries: int = 3) -> dict:
        """Load a model into Ollama."""
        try:
            self._log_debug("start_load", {"model_name": name})
            
            version_num, use_new_schema = await self.get_ollama_version()
            self._log_debug("version_check", {
                "version": version_num,
                "use_new_schema": use_new_schema
            })
            
            model_name = self._sanitize_tag(name)
            self._log_debug("name_normalized", {
                "original": name,
                "normalized": model_name
            })
            
            if not name.endswith(".gguf"):
                try:
                    payload = {"name": model_name}
                    url = self.client.base_url.join("/api/pull")
                    self._log_debug("pull_start", {"url": str(url), "payload": payload})
                    
                    response = await self.client.post("/api/pull", json=payload, timeout=120.0)
                    body = await response.aread()
                    self._log_debug("pull_response", {
                        "status_code": response.status_code,
                        "body": body.decode() if isinstance(body, bytes) else body
                    })
                    
                    response.raise_for_status()
                    return {"status": "success"}
                except httpx.HTTPStatusError as e:
                    raw = await e.response.aread()
                    self._log_error("Pull failed", {
                        "stage": "pull",
                        "status_code": e.response.status_code,
                        "response": raw.decode() if isinstance(raw, bytes) else raw
                    })
                    raise self.ModelError("Model not found in remote repository", "pull", e.response.status_code)
                except Exception as e:
                    self._log_error("Pull failed", {"stage": "pull", "error": str(e)})
                    raise self.ModelError(str(e), "pull")

            model_path = self.resolve_model_path(name)
            self._log_debug("path_resolved", {"path": model_path})
            
            try:
                self.validate_model_file(model_path)
            except (FileNotFoundError, PermissionError) as e:
                self._log_error("Model file validation failed", {
                    "stage": "validation",
                    "path": model_path,
                    "error": str(e)
                })
                raise self.ModelError(str(e), "validation")
            
            for attempt in range(max_retries):
                try:
                    payload = {
                        "name": model_name,
                        "from": model_path,
                        "stream": False
                    }
                    
                    url = self.client.base_url.join("/api/create")
                    self._log_debug("create_start", {
                        "attempt": attempt + 1,
                        "url": str(url),
                        "payload": payload,
                        "ollama_version": version_num,
                        "request_headers": dict(self.client.headers),
                        "model_path_exists": os.path.exists(model_path),
                        "model_path_readable": os.access(model_path, os.R_OK) if os.path.exists(model_path) else False,
                        "model_path_size": os.path.getsize(model_path) if os.path.exists(model_path) else 0,
                        "model_path_permissions": oct(os.stat(model_path).st_mode)[-3:] if os.path.exists(model_path) else None,
                        "model_path_owner": os.stat(model_path).st_uid if os.path.exists(model_path) else None,
                        "model_path_group": os.stat(model_path).st_gid if os.path.exists(model_path) else None
                    })
                    
                    # Log the exact request we're about to make
                    print(f"\n[DEBUG] Sending request to {url}")
                    print(f"[DEBUG] Headers: {dict(self.client.headers)}")
                    print(f"[DEBUG] Payload: {json.dumps(payload, indent=2)}")
                    print(f"[DEBUG] Model path: {model_path}")
                    print(f"[DEBUG] Model exists: {os.path.exists(model_path)}")
                    print(f"[DEBUG] Model readable: {os.access(model_path, os.R_OK) if os.path.exists(model_path) else False}")
                    print(f"[DEBUG] Model size: {os.path.getsize(model_path) if os.path.exists(model_path) else 0} bytes")
                    print(f"[DEBUG] Model permissions: {oct(os.stat(model_path).st_mode)[-3:] if os.path.exists(model_path) else None}")
                    print(f"[DEBUG] Model owner: {os.stat(model_path).st_uid if os.path.exists(model_path) else None}")
                    print(f"[DEBUG] Model group: {os.stat(model_path).st_gid if os.path.exists(model_path) else None}\n")
                    
                    # Use regular request instead of streaming
                    response = await self.client.post("/api/create", json=payload, timeout=120.0)
                    raw_response = await response.aread()
                    response_text = raw_response.decode(errors="ignore")
                    
                    if response.status_code >= 400:
                        self._log_error("Create failed", {
                            "stage": "create",
                            "attempt": attempt + 1,
                            "status_code": response.status_code,
                            "response": response_text
                        })
                        raise self.ModelError(f"Model creation failed: {response_text}", "create", response.status_code)
                    
                    try:
                        result = json.loads(response_text)
                        if "error" in result:
                            error_message = result["error"]
                            self._log_error("Ollama error", {
                                "stage": "create",
                                "attempt": attempt + 1,
                                "error": error_message
                            })
                            raise self.ModelError(error_message, "create")
                        
                        if result.get("status") == "success":
                            self._log_debug("create_success", {"attempt": attempt + 1})
                            if not await self.wait_for_model(model_name):
                                raise self.ModelError("Model failed to load within timeout", "create")
                            return {"status": "success"}
                    except json.JSONDecodeError as e:
                        self._log_error("Invalid response", {
                            "stage": "create",
                            "attempt": attempt + 1,
                            "error": str(e),
                            "response": response_text
                        })
                        raise self.ModelError(f"Invalid response from Ollama: {str(e)}", "create")
                except self.ModelError:
                    raise
                except Exception as e:
                    self._log_error("Load attempt failed", {
                        "stage": "create",
                        "attempt": attempt + 1,
                        "error": str(e)
                    })
                    if attempt == max_retries - 1:
                        raise self.ModelError(f"Failed after {max_retries} attempts", "create")
                    await asyncio.sleep(2 ** attempt)
            
            raise self.ModelError(f"Failed after {max_retries} attempts", "create")
        except self.ModelError:
            raise
        except Exception as e:
            self._log_error("Unhandled error", {"error": str(e)})
            raise self.ModelError(str(e), "unknown") 