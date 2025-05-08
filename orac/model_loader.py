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
import time
import subprocess
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

    def _log_debug(self, stage: str, data: Dict):
        """Add debug information with stage and data."""
        log_entry = {
            "stage": stage,
            "timestamp": asyncio.get_event_loop().time(),
            "data": data
        }
        self._debug_logs.append(log_entry)

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
            response = await self.client.get("/api/version")
            body = await response.aread()
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
            self._log_error(f"Failed to get Ollama version: {str(e)}")
        except Exception as e:
            self._log_error(f"Failed to get Ollama version: {str(e)}")
        return 0.0, True  # Default to new schema on error

    def _sanitize_tag(self, name: str) -> str:
        """
        Sanitize model name to be compatible with Ollama's naming rules:
        - Must be lowercase
        - Can only contain a-z, 0-9, and hyphens
        - Must start with a letter
        - Maximum length of 64 characters
        - No consecutive hyphens
        - No leading/trailing hyphens
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
        
        # Ensure it starts with a letter
        if not base_name or not base_name[0].isalpha():
            base_name = 'm-' + base_name
        
        # Truncate to max length if needed
        if len(base_name) > 64:
            base_name = base_name[:64]
            # Ensure we don't end with a hyphen
            base_name = base_name.rstrip('-')
        
        # Handle tag specification (e.g., "model:tag")
        if ":" in base_name:
            model, tag = base_name.split(":", 1)
            # Ensure tag also follows naming rules
            tag = re.sub(r'[^a-z0-9-]', '', tag.lower())
            tag = re.sub(r'-{2,}', '-', tag).strip('-')
            if not tag or not tag[0].isalpha():
                tag = 't-' + tag
            if len(tag) > 64:
                tag = tag[:64].rstrip('-')
            return f"{model}:{tag}"
        
        return base_name

    def normalize_model_name(self, name: str) -> str:
        """Convert model name to valid Ollama tag format."""
        return self._sanitize_tag(name)

    def resolve_model_path(self, name: str) -> str:
        """Resolve the full path to a model file."""
        # Try environment variable first
        model_base_path = os.getenv("OLLAMA_MODEL_PATH")
        if not model_base_path:
            # Fallback to default paths
            default_paths = [
                "/models/gguf",  # Docker default
                os.path.expanduser("~/models/gguf"),  # User home
                os.path.join(os.getcwd(), "models", "gguf")  # Current directory
            ]
            
            for path in default_paths:
                if os.path.exists(path):
                    model_base_path = path
                    break
            
            if not model_base_path:
                model_base_path = default_paths[0]  # Use Docker default if no path exists
        
        # Ensure the .gguf extension is present
        if not name.endswith(".gguf"):
            name = f"{name}.gguf"
        
        model_path = os.path.join(model_base_path, name)
        self._log_debug("model_path_resolved", {
            "base_path": model_base_path,
            "model_name": name,
            "full_path": model_path,
            "exists": os.path.exists(model_path)
        })
        return model_path

    def validate_model_file(self, path: str) -> None:
        """Validate that model file exists and is readable."""
        if not os.path.exists(path):
            raise FileNotFoundError(f"Model file not found at {path}")
        if not os.access(path, os.R_OK):
            raise PermissionError(f"Model file not readable at {path}")

    def create_modelfile(self, model_path: str, use_new_schema: bool) -> str:
        """Create appropriate Modelfile content based on schema version."""
        modelfile = []
        
        # Use relative path for the model file
        model_filename = os.path.basename(model_path)
        modelfile.append(f"FROM {model_filename}")
        
        # Add metadata
        modelfile.append("")
        modelfile.append("# Model metadata")
        modelfile.append(f"PARAMETER temperature 0.7")
        modelfile.append(f"PARAMETER top_p 0.7")
        modelfile.append(f"PARAMETER top_k 40")
        modelfile.append(f"PARAMETER repeat_penalty 1.1")
        modelfile.append(f"PARAMETER stop \"<|im_end|>\"")
        modelfile.append(f"PARAMETER stop \"<|endoftext|>\"")
        
        return "\n".join(modelfile)

    def write_modelfile_to_temp(self, modelfile_content: str) -> Tuple[str, bool]:
        """Write Modelfile content to a temporary file and return its path and whether it was created."""
        # Create temporary file in the same directory as the model
        model_dir = os.path.dirname(modelfile_content.split("FROM ")[1].strip())
        temp_modelfile = os.path.join(model_dir, "Modelfile")
        
        try:
            with open(temp_modelfile, "w") as f:
                f.write(modelfile_content)
            return temp_modelfile, True
        except Exception as e:
            self._log_error("Failed to write Modelfile", {
                "path": temp_modelfile,
                "error": str(e)
            })
            raise Exception(f"Failed to write Modelfile: {str(e)}")

    async def wait_for_model(self, model_name: str, max_retries: int = 60, delay: float = 5.0) -> bool:
        """Wait for a model to be ready."""
        for i in range(max_retries):
            try:
                self._log_debug("checking_model_status", {
                    "attempt": i + 1,
                    "model_name": model_name
                })
                
                response = await self.client.post("/api/show", json={"name": model_name})
                if response.status_code == 200:
                    self._log_debug("model_ready", {
                        "attempt": i + 1,
                        "model_name": model_name
                    })
                    return True
                
                response = await self.client.get("/api/tags")
                if response.status_code == 200:
                    models = response.json().get("models", [])
                    if any(model.get("name") == model_name for model in models):
                        self._log_debug("model_found_in_tags", {
                            "attempt": i + 1,
                            "model_name": model_name
                        })
                        return True
            except Exception as e:
                self._log_error(f"Error checking model status: {str(e)}")
            
            if i < max_retries - 1:
                self._log_debug("waiting_for_model", {
                    "attempt": i + 1,
                    "delay": delay,
                    "model_name": model_name
                })
                await asyncio.sleep(delay)
        
        self._log_error("Model load timeout", {
            "model_name": model_name,
            "max_retries": max_retries,
            "total_time": max_retries * delay
        })
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
            start_time = time.time()
            self._log_debug("start_load", {
                "model_name": name,
                "start_time": start_time
            })
            
            version_num, use_new_schema = await self.get_ollama_version()
            self._log_debug("version_check", {
                "version": version_num,
                "use_new_schema": use_new_schema,
                "elapsed_time": time.time() - start_time
            })
            
            model_name = self._sanitize_tag(name)
            self._log_debug("name_normalized", {
                "original": name,
                "normalized": model_name,
                "elapsed_time": time.time() - start_time
            })
            
            model_path = self.resolve_model_path(name)
            
            # Log detailed file stats
            self._log_debug("model_file_stats", {
                "path": model_path,
                "exists": os.path.exists(model_path),
                "is_file": os.path.isfile(model_path),
                "size": os.path.getsize(model_path) if os.path.exists(model_path) else None,
                "permissions": oct(os.stat(model_path).st_mode)[-3:] if os.path.exists(model_path) else None,
                "elapsed_time": time.time() - start_time
            })
            
            try:
                self.validate_model_file(model_path)
            except (FileNotFoundError, PermissionError) as e:
                self._log_error("Model file validation failed", {
                    "stage": "validation",
                    "path": model_path,
                    "error": str(e),
                    "elapsed_time": time.time() - start_time
                })
                raise self.ModelError(str(e), "validation")
            
            for attempt in range(max_retries):
                try:
                    # Log system state before model load
                    try:
                        ps_output = subprocess.run(["ps", "aux"], capture_output=True, text=True)
                        top_output = subprocess.run(["top", "-bn1"], capture_output=True, text=True)
                        self._log_debug("system_state_before_load", {
                            "ps_output": ps_output.stdout,
                            "top_output": top_output.stdout,
                            "elapsed_time": time.time() - start_time
                        })
                    except Exception as e:
                        self._log_error("Failed to get system state", {
                            "error": str(e),
                            "elapsed_time": time.time() - start_time
                        })
                    
                    # Create Modelfile content
                    modelfile_content = self.create_modelfile(model_path, use_new_schema)
                    modelfile_path, is_temp = self.write_modelfile_to_temp(modelfile_content)
                    
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
                            "model_path_group": os.stat(model_path).st_gid if os.path.exists(model_path) else None,
                            "elapsed_time": time.time() - start_time
                        })
                        
                        # Use regular request instead of streaming with increased timeout
                        response = await self.client.post("/api/create", json=payload, timeout=300.0)
                        raw_response = await response.aread()
                        response_text = raw_response.decode(errors="ignore")
                        
                        # Log raw response
                        self._log_debug("create_raw_response", {
                            "status_code": response.status_code,
                            "raw_body": response_text,
                            "elapsed_time": time.time() - start_time
                        })
                        
                        if response.status_code >= 400:
                            self._log_error("Create failed", {
                                "stage": "create",
                                "attempt": attempt + 1,
                                "status_code": response.status_code,
                                "response": response_text,
                                "elapsed_time": time.time() - start_time
                            })
                            raise self.ModelError(f"Model creation failed: {response_text}", "create", response.status_code)
                        
                        try:
                            result = json.loads(response_text)
                            if "error" in result:
                                error_message = result["error"]
                                self._log_error("Ollama error", {
                                    "stage": "create",
                                    "attempt": attempt + 1,
                                    "error": error_message,
                                    "elapsed_time": time.time() - start_time
                                })
                                raise self.ModelError(error_message, "create")
                                
                            if result.get("status") == "success":
                                self._log_debug("create_success", {
                                    "attempt": attempt + 1,
                                    "elapsed_time": time.time() - start_time
                                })
                                if not await self.wait_for_model(model_name):
                                    raise self.ModelError("Model failed to load within timeout", "create")
                                return {"status": "success"}
                        except json.JSONDecodeError as e:
                            self._log_error("Invalid response", {
                                "stage": "create",
                                "attempt": attempt + 1,
                                "error": str(e),
                                "response": response_text,
                                "elapsed_time": time.time() - start_time
                            })
                            raise self.ModelError(f"Invalid response from Ollama: {str(e)}", "create")
                    finally:
                        # Clean up temporary Modelfile if we created one
                        if is_temp and os.path.exists(modelfile_path):
                            try:
                                os.unlink(modelfile_path)
                            except Exception as e:
                                self._log_error("Failed to clean up Modelfile", {
                                    "path": modelfile_path,
                                    "error": str(e),
                                    "elapsed_time": time.time() - start_time
                                })
                except self.ModelError:
                    raise
                except Exception as e:
                    self._log_error("Load attempt failed", {
                        "stage": "create",
                        "attempt": attempt + 1,
                        "error": str(e),
                        "elapsed_time": time.time() - start_time
                    })
                    if attempt == max_retries - 1:
                        raise self.ModelError(f"Failed after {max_retries} attempts", "create")
                    await asyncio.sleep(2 ** attempt)
            
            raise self.ModelError(f"Failed after {max_retries} attempts", "create")
        except self.ModelError:
            raise
        except Exception as e:
            self._log_error("Unhandled error", {
                "error": str(e),
                "elapsed_time": time.time() - start_time
            })
            raise self.ModelError(str(e), "unknown") 