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
import logging
import psutil
from typing import Optional, Tuple, List, Dict, NamedTuple
import httpx
from pathlib import Path

# Constants
MODEL_LOAD_TIMEOUT = 600.0  # 10 minutes timeout for model loading
MODEL_LOAD_RETRY_DELAY = 5.0  # 5 seconds between retries
MAX_MODEL_LOAD_RETRIES = 3  # Maximum number of retries for model loading

# Default log directory - use absolute path in project root
DEFAULT_LOG_DIR = os.getenv("ORAC_LOG_DIR", os.path.join(os.path.dirname(os.path.dirname(__file__)), "logs"))

def setup_logging():
    """Configure logging to both console and file."""
    # Create logs directory if it doesn't exist
    log_dir = Path(DEFAULT_LOG_DIR)
    log_dir.mkdir(exist_ok=True, parents=True)
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    
    # Remove any existing handlers to avoid duplicate logs
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Console handler - INFO level
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(levelname)s: %(message)s')
    console_handler.setFormatter(console_formatter)
    
    # File handler - DEBUG level with more details
    file_handler = logging.FileHandler(log_dir / "model_loader.log")
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s\n'
        'Context: %(context)s\n'
        'Traceback: %(traceback)s'
    )
    file_handler.setFormatter(file_formatter)
    
    # Add handlers to root logger
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    return root_logger

# Initialize logging
logger = setup_logging()

class ModelError(Exception):
    """Base class for model loading errors."""
    def __init__(self, message: str, stage: str, status_code: int = None):
        self.message = message
        self.stage = stage
        self.status_code = status_code
        super().__init__(f"{stage}: {message}")

class NetworkError(ModelError):
    """Network-related errors during model operations."""
    def __init__(self, message: str, status_code: int = None):
        super().__init__(message, "network", status_code)

class PermissionError(ModelError):
    """Permission-related errors during model operations."""
    def __init__(self, message: str, status_code: int = None):
        super().__init__(message, "permission", status_code)

class ResourceError(ModelError):
    """Resource-related errors during model operations."""
    def __init__(self, message: str, status_code: int = None):
        super().__init__(message, "resource", status_code)

class ConfigurationError(ModelError):
    """Configuration-related errors during model operations."""
    def __init__(self, message: str, status_code: int = None):
        super().__init__(message, "configuration", status_code)

class ModelSize(NamedTuple):
    """Model size information."""
    parameters: int
    size_bytes: int
    is_large: bool

class ModelLoader:
    def __init__(self, client: httpx.AsyncClient):
        self.client = client
        self._error_logs: List[str] = []
        self._debug_logs: List[Dict] = []
        self._log_dir = Path(DEFAULT_LOG_DIR)
        self._start_time = None
        self._health_check_interval = 300  # 5 minutes
        self._last_health_check = {}
        self._model_semaphore = asyncio.Semaphore(2)  # Limit concurrent model loads
        self._memory_threshold = 0.9  # 90% memory usage threshold
        self._large_model_threshold = 7_000_000_000  # 7B parameters

    def _log_error(self, message: str, context: Dict = None):
        """Log error to both console and file with different detail levels."""
        # Console logging - high level
        logger.error(message)
        
        # File logging - detailed
        extra = {
            'context': json.dumps(context, indent=2) if context else '{}',
            'traceback': traceback.format_exc()
        }
        logger.debug(f"Detailed error: {message}", extra=extra)
        
        # Store in memory logs
        log_entry = {"message": message}
        if context:
            log_entry.update(context)
        self._error_logs.append(json.dumps(log_entry))

    def _log_debug(self, stage: str, data: Dict):
        """Log debug information with stage and data."""
        # Console logging - minimal
        if stage in ["start_load", "create_success", "model_ready"]:
            logger.info(f"{stage}: {data.get('model_name', 'unknown')}")
        
        # File logging - detailed
        extra = {
            'context': json.dumps(data, indent=2),
            'traceback': ''
        }
        logger.debug(f"Stage: {stage}", extra=extra)
        
        # Store in memory logs
        log_entry = {
            "stage": stage,
            "timestamp": time.time(),
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
            
            if not model_base_path:
                model_base_path = default_paths[0]  # Use Docker default if no path exists
        
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

    def validate_model_file(self, path: str) -> None:
        """Validate that model file exists and is readable."""
        if not os.path.exists(path):
            self._log_error(f"Model file not found: {path}")
            raise self.ModelError(f"Model file not found: {path}", "validation")
        if not os.access(path, os.R_OK):
            self._log_error(f"Model file not readable: {path}")
            raise self.ModelError(f"Model file not readable: {path}", "validation")

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

    def _estimate_model_size(self, model_path: str) -> ModelSize:
        """Estimate model size from filename and file size."""
        file_size = os.path.getsize(model_path)
        
        # Try to extract parameter count from filename
        param_match = re.search(r'(\d+(?:\.\d+)?)[Bb]', os.path.basename(model_path))
        if param_match:
            param_str = param_match.group(1)
            if '.' in param_str:
                # Handle decimal billions (e.g., 1.5B)
                params = int(float(param_str) * 1_000_000_000)
            else:
                # Handle integer billions (e.g., 7B)
                params = int(param_str) * 1_000_000_000
        else:
            # Fallback: estimate from file size (rough approximation)
            params = int(file_size / 2)  # Assume 2 bytes per parameter
        
        return ModelSize(
            parameters=params,
            size_bytes=file_size,
            is_large=params >= self._large_model_threshold
        )

    def _check_memory_usage(self) -> bool:
        """Check if system has enough memory available."""
        memory = psutil.virtual_memory()
        return memory.percent < (self._memory_threshold * 100)

    async def _wait_for_memory(self, timeout: float = 300.0) -> bool:
        """Wait for memory to become available."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self._check_memory_usage():
                return True
            await asyncio.sleep(5.0)
        return False

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
        try:
            model_path = self.resolve_model_path(name)
            self.validate_model_file(model_path)
            
            # Check model size and memory requirements
            model_size = self._estimate_model_size(model_path)
            self._log_debug("model_size_check", {
                "model_name": model_name,
                "parameters": model_size.parameters,
                "size_bytes": model_size.size_bytes,
                "is_large": model_size.is_large
            })
            
            if model_size.is_large:
                if not self._check_memory_usage():
                    self._log_debug("waiting_for_memory", {
                        "model_name": model_name,
                        "memory_percent": psutil.virtual_memory().percent
                    })
                    if not await self._wait_for_memory():
                        raise ResourceError("Insufficient memory available for large model")
        except Exception as e:
            raise self._classify_error(e)
        
        # Get Ollama version and create Modelfile
        try:
            version_num, use_new_schema = await self.get_ollama_version()
            modelfile_content = self.create_modelfile(model_path, use_new_schema)
            modelfile_path, is_temp = self.write_modelfile_to_temp(modelfile_content)
        except Exception as e:
            raise self._classify_error(e)
        
        # Initialize exponential backoff parameters
        base_delay = 1.0  # Start with 1 second
        max_delay = 30.0  # Maximum delay of 30 seconds
        retry_count = 0
        
        # Use semaphore to limit concurrent model loads
        async with self._model_semaphore:
            while retry_count < max_retries:
                try:
                    # Prepare version-specific payload
                    if use_new_schema:
                        payload = {
                            "name": model_name,
                            "path": os.path.dirname(model_path),  # Directory containing both model and Modelfile
                            "stream": True
                        }
                    else:
                        payload = {
                            "name": model_name,
                            "modelfile": modelfile_content,
                            "stream": True
                        }
                    
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
                                            "elapsed_time": time.time() - start_time,
                                            "retry_count": retry_count
                                        })
                                    # Check for completion
                                    if data.get("status") == "success":
                                        self._log_debug("model_load_success", {
                                            "model_name": model_name,
                                            "elapsed_time": time.time() - start_time,
                                            "retry_count": retry_count
                                        })
                                        return {"status": "success"}
                                except json.JSONDecodeError:
                                    continue
                    
                    # If we get here, the model load was successful
                    break
                    
                except Exception as e:
                    retry_count += 1
                    if retry_count >= max_retries:
                        self._log_error(f"Model load failed after {max_retries} retries: {str(e)}")
                        raise self._classify_error(e)
                    
                    # Calculate exponential backoff delay
                    delay = min(base_delay * (2 ** (retry_count - 1)), max_delay)
                    self._log_debug("model_load_retry", {
                        "model_name": model_name,
                        "retry_count": retry_count,
                        "delay": delay,
                        "error": str(e)
                    })
                    await asyncio.sleep(delay)
        
        # Verify model is ready and perform initial health check
        try:
            if await self.verify_model_status(model_name):
                # Perform initial health check
                if await self.check_model_health(model_name):
                    return {"status": "success"}
                else:
                    raise ResourceError("Model failed initial health check")
        except Exception as e:
            raise self._classify_error(e)
        
        raise ResourceError("Failed to load model within timeout")

    async def check_model_health(self, model_name: str) -> bool:
        """Check if a model is healthy and responsive."""
        current_time = time.time()
        last_check = self._last_health_check.get(model_name, 0)
        
        # Only perform health check if enough time has passed
        if current_time - last_check < self._health_check_interval:
            return True
            
        try:
            # Try a simple prompt to verify model responsiveness
            response = await self.client.post(
                "/api/generate",
                json={
                    "model": model_name,
                    "prompt": "test",
                    "stream": False
                },
                timeout=10.0
            )
            response.raise_for_status()
            self._last_health_check[model_name] = current_time
            return True
        except Exception as e:
            self._log_error(f"Health check failed for model {model_name}: {str(e)}")
            return False

    async def reload_unhealthy_model(self, model_name: str) -> bool:
        """Attempt to reload a model that failed health check."""
        try:
            # First try to unload the model
            await self.client.delete("/api/delete", json={"name": model_name})
            
            # Then reload it
            async with self._model_semaphore:
                result = await self.load_model(model_name)
                return result["status"] == "success"
        except Exception as e:
            self._log_error(f"Failed to reload unhealthy model {model_name}: {str(e)}")
            return False

    def _classify_error(self, error: Exception) -> ModelError:
        """Classify an error into the appropriate error category."""
        if isinstance(error, httpx.HTTPStatusError):
            status_code = error.response.status_code
            if status_code in (401, 403):
                return PermissionError(str(error), status_code)
            elif status_code in (404, 409):
                return ResourceError(str(error), status_code)
            elif status_code >= 500:
                return NetworkError(str(error), status_code)
            else:
                return ConfigurationError(str(error), status_code)
        elif isinstance(error, httpx.RequestError):
            return NetworkError(str(error))
        elif isinstance(error, OSError):
            if error.errno in (13, 30):  # Permission denied, Read-only file system
                return PermissionError(str(error))
            else:
                return ResourceError(str(error))
        else:
            return ModelError(str(error), "unknown")

    async def cleanup(self):
        """Clean up any temporary resources."""
        try:
            # Clean up any temporary Modelfiles
            model_dir = os.path.dirname(self.resolve_model_path("dummy.gguf"))
            temp_modelfile = os.path.join(model_dir, "Modelfile")
            if os.path.exists(temp_modelfile):
                try:
                    os.unlink(temp_modelfile)
                    self._log_debug("cleanup", {
                        "action": "removed_temp_modelfile",
                        "path": temp_modelfile
                    })
                except Exception as e:
                    self._log_error("Failed to clean up Modelfile", {
                        "path": temp_modelfile,
                        "error": str(e)
                    })
        except Exception as e:
            self._log_error("Cleanup failed", {
                "error": str(e)
            }) 