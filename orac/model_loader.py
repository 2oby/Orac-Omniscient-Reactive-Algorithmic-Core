"""
orac.model_loader
----------------
Handles model loading and management for Ollama, optimized for Jetson Orin Nano.

Key features:
- Memory-efficient model loading with configurable parameters
- Proper error handling and recovery
- Detailed logging for troubleshooting
- Jetson-specific optimizations
"""

import os
import json
import asyncio
import re
import time
from typing import Dict, List, Tuple, Optional, Any
import httpx

from orac.logger import get_logger

logger = get_logger(__name__)

# Constants - configurable via environment variables for different Jetson models
MODEL_LOAD_TIMEOUT = float(os.environ.get("MODEL_LOAD_TIMEOUT", "600.0"))  # 10 minutes
MODEL_LOAD_RETRY_DELAY = float(os.environ.get("MODEL_LOAD_RETRY_DELAY", "5.0"))  # 5 seconds
MAX_MODEL_LOAD_RETRIES = int(os.environ.get("MAX_MODEL_LOAD_RETRIES", "3"))

# Jetson-specific memory optimizations
GPU_LAYERS = int(os.environ.get("GPU_LAYERS", "-1"))  # -1 means auto-detect
CPU_THREADS = int(os.environ.get("CPU_THREADS", "4"))  # Default for Orin Nano is 4 cores


class ModelError(Exception):
    """Custom exception for model loading errors."""
    def __init__(self, message: str, stage: str, status_code: Optional[int] = None):
        self.message = message
        self.stage = stage
        self.status_code = status_code
        super().__init__(f"{stage}: {message}")


class ModelLoader:
    def __init__(self, client: httpx.AsyncClient):
        """Initialize the model loader with an HTTP client."""
        self.client = client
        self.start_time = time.time()
        logger.info("ModelLoader initialized")

    async def get_ollama_version(self) -> Tuple[float, bool]:
        """Get Ollama version and determine if new schema should be used."""
        try:
            logger.debug("Checking Ollama version")
            response = await self.client.get("/api/version")
            response.raise_for_status()
            version = response.json().get("version", "0.0.0")
            
            # Parse version number
            version_parts = version.split('.')
            if len(version_parts) >= 2:
                major = int(version_parts[0])
                minor = int(version_parts[1])
                version_num = float(f"{major}.{minor}")
                use_new_schema = version_num >= 0.6
                
                logger.info(f"Ollama version: {version} (parsed as {version_num}, using new schema: {use_new_schema})")
                return version_num, use_new_schema
        except Exception as e:
            logger.error(f"Failed to get Ollama version: {str(e)}")
        
        # Default to new schema on error
        logger.warning("Using default version 0.0 with new schema due to error")
        return 0.0, True

    def normalize_model_name(self, name: str) -> str:
        """Convert model name to valid Ollama tag format."""
        # Hard code the model name for now
        return "Qwen3-0.6B-Q4_K_M"
        
        # Original normalization code commented out for reference
        # # Remove .gguf extension and convert to lowercase
        # base_name = name.removesuffix(".gguf").lower()
        # 
        # # Replace dots and underscores with hyphens
        # base_name = re.sub(r'[._]+', '-', base_name)
        # 
        # # Remove any other special characters except alphanumeric and hyphens
        # base_name = re.sub(r'[^a-z0-9-]', '', base_name)
        # 
        # # Normalize multiple hyphens to single hyphen
        # base_name = re.sub(r'-{2,}', '-', base_name)
        # 
        # # Remove leading/trailing hyphens
        # base_name = base_name.strip('-')
        # 
        # # Ensure it starts with a letter
        # if not base_name or not base_name[0].isalpha():
        #     base_name = 'm-' + base_name
        # 
        # # Truncate to max length if needed (64 chars for Ollama)
        # if len(base_name) > 64:
        #     base_name = base_name[:64].rstrip('-')
        # 
        # logger.debug(f"Normalized model name from '{name}' to '{base_name}'")
        # return base_name

    def resolve_model_path(self, name: str) -> str:
        """Resolve the full path to a model file."""
        # Try environment variable first
        model_base_path = os.environ.get("OLLAMA_MODEL_PATH")
        if not model_base_path:
            # Fallback to default paths with Jetson-friendly locations
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
        
        # Log detailed information for debugging
        exists = os.path.exists(model_path)
        logger.debug(f"Resolved model path: {model_path} (exists: {exists})")
        
        if exists:
            try:
                # Log file size to help with memory requirement estimation
                size_mb = os.path.getsize(model_path) / (1024 * 1024)
                logger.info(f"Model file size: {size_mb:.2f} MB")
            except Exception as e:
                logger.warning(f"Couldn't get model file size: {str(e)}")
        
        return model_path

    def validate_model_file(self, path: str) -> None:
        """Validate that model file exists and is readable."""
        if not os.path.exists(path):
            logger.error(f"Model file not found: {path}")
            raise FileNotFoundError(f"Model file not found at {path}")
        
        if not os.path.isfile(path):
            logger.error(f"Path is not a file: {path}")
            raise FileNotFoundError(f"Path is not a file: {path}")
        
        if not os.access(path, os.R_OK):
            logger.error(f"Model file not readable: {path}")
            raise PermissionError(f"Model file not readable at {path}")
        
        logger.info(f"Model file validated: {path}")

    def create_modelfile(self, model_path: str, use_new_schema: bool) -> str:
        """Create appropriate Modelfile content based on schema version and Jetson optimizations."""
        modelfile = []
        
        # Use relative path for the model file
        model_filename = os.path.basename(model_path)
        modelfile.append(f"FROM {model_filename}")
        
        # Add metadata and Jetson-specific optimizations
        modelfile.append("")
        modelfile.append("# Model metadata")
        modelfile.append(f"PARAMETER temperature 0.7")
        modelfile.append(f"PARAMETER top_p 0.7")
        modelfile.append(f"PARAMETER top_k 40")
        modelfile.append(f"PARAMETER repeat_penalty 1.1")
        modelfile.append(f"PARAMETER stop \"<|im_end|>\"")
        modelfile.append(f"PARAMETER stop \"<|endoftext|>\"")
        
        # Jetson Orin Nano specific optimizations
        if GPU_LAYERS != -1:
            modelfile.append(f"PARAMETER gpu_layers {GPU_LAYERS}")
        
        modelfile.append(f"PARAMETER num_thread {CPU_THREADS}")
        
        # Add context window optimization based on Jetson memory constraints
        # Orin Nano typically has 8GB shared memory, so we need to be careful with context size
        modelfile.append(f"PARAMETER num_ctx 2048")  # Conservative default for Jetson
        
        modelfile_content = "\n".join(modelfile)
        logger.debug(f"Created Modelfile:\n{modelfile_content}")
        return modelfile_content

    def write_modelfile(self, modelfile_content: str, model_path: str) -> Tuple[str, bool]:
        """Write Modelfile content to appropriate location."""
        # Create the Modelfile in the same directory as the model
        model_dir = os.path.dirname(model_path)
        modelfile_path = os.path.join(model_dir, "Modelfile")
        
        try:
            with open(modelfile_path, "w") as f:
                f.write(modelfile_content)
            logger.info(f"Wrote Modelfile to {modelfile_path}")
            return modelfile_path, True
        except Exception as e:
            logger.error(f"Failed to write Modelfile: {str(e)}")
            raise Exception(f"Failed to write Modelfile: {str(e)}")

    async def wait_for_model(self, model_name: str, max_retries: int = 60, delay: float = 5.0) -> bool:
        """Wait for a model to be ready with detailed status checking."""
        logger.info(f"Waiting for model {model_name} to be ready (max {max_retries} attempts, {delay}s delay)")
        
        for i in range(max_retries):
            try:
                logger.debug(f"Checking model status (attempt {i+1}/{max_retries})")
                
                # Check model status via show endpoint
                response = await self.client.post("/api/show", json={"name": model_name})
                if response.status_code == 200:
                    logger.info(f"Model {model_name} is ready!")
                    return True
                
                # Check model presence in tags
                response = await self.client.get("/api/tags")
                if response.status_code == 200:
                    models = response.json().get("models", [])
                    model = next((m for m in models if m.get("name") == model_name), None)
                    if model:
                        logger.info(f"Model {model_name} found in tags")
                        return True
                
                logger.debug(f"Model {model_name} not ready yet (attempt {i+1}/{max_retries})")
            except Exception as e:
                logger.warning(f"Error checking model status: {str(e)}")
            
            if i < max_retries - 1:
                logger.debug(f"Waiting {delay}s before next check")
                await asyncio.sleep(delay)
        
        logger.error(f"Model {model_name} failed to load within timeout ({max_retries * delay}s)")
        return False

    async def load_model(self, name: str, max_retries: int = MAX_MODEL_LOAD_RETRIES) -> Dict[str, Any]:
        """
        Load a model into Ollama with Jetson-specific optimizations.
        
        Args:
            name: The model name or path
            max_retries: Maximum number of load attempts
            
        Returns:
            Dict with status and message
            
        Raises:
            ModelError: If model loading fails
        """
        start_time = time.time()
        logger.info(f"Starting model load process for {name}")
        
        try:
            # Check if model is already loaded
            normalized_name = self.normalize_model_name(name)
            try:
                response = await self.client.post("/api/show", json={"name": normalized_name})
                if response.status_code == 200:
                    logger.info(f"Model {normalized_name} is already loaded")
                    return {"status": "success", "message": "Model already loaded"}
            except Exception as e:
                logger.debug(f"Model {normalized_name} not loaded: {str(e)}")
            
            # Get Ollama version
            version_num, use_new_schema = await self.get_ollama_version()
            logger.info(f"Using Ollama version {version_num} (new schema: {use_new_schema})")
            
            # Resolve model path
            model_path = self.resolve_model_path(name)
            
            # Validate model file
            try:
                self.validate_model_file(model_path)
            except (FileNotFoundError, PermissionError) as e:
                logger.error(f"Model validation failed: {str(e)}")
                raise ModelError(str(e), "validation")
            
            # Create and write modelfile
            modelfile_content = self.create_modelfile(model_path, use_new_schema)
            try:
                modelfile_path, is_temp_file = self.write_modelfile(modelfile_content, model_path)
            except Exception as e:
                logger.error(f"Failed to create Modelfile: {str(e)}")
                raise ModelError(str(e), "modelfile_creation")
            
            # Prepare load parameters with Jetson optimizations
            for attempt in range(max_retries):
                try:
                    logger.info(f"Loading model {normalized_name} (attempt {attempt+1}/{max_retries})")
                    
                    # Prepare the payload
                    payload = {
                        "name": normalized_name,
                        "path": model_path,
                        "stream": False
                    }
                    
                    # Log the request details
                    logger.debug(f"Create request payload: {json.dumps(payload)}")
                    
                    # Send the create request
                    response = await self.client.post(
                        "/api/create", 
                        json=payload,
                        timeout=MODEL_LOAD_TIMEOUT
                    )
                    
                    # Handle the response
                    if response.status_code >= 400:
                        error_text = await response.text()
                        logger.error(f"Create failed with status {response.status_code}: {error_text}")
                        if attempt < max_retries - 1:
                            logger.info(f"Retrying in {MODEL_LOAD_RETRY_DELAY} seconds")
                            await asyncio.sleep(MODEL_LOAD_RETRY_DELAY)
                            continue
                        raise ModelError(
                            f"Failed to create model: {error_text}", 
                            "create", 
                            response.status_code
                        )
                    
                    # Parse response
                    response_json = response.json()
                    if "error" in response_json:
                        error_message = response_json["error"]
                        logger.error(f"Ollama error: {error_message}")
                        if attempt < max_retries - 1:
                            logger.info(f"Retrying in {MODEL_LOAD_RETRY_DELAY} seconds")
                            await asyncio.sleep(MODEL_LOAD_RETRY_DELAY)
                            continue
                        raise ModelError(error_message, "create")
                    
                    # Wait for model to be ready
                    logger.info("Model creation successful, waiting for model to be ready")
                    if await self.wait_for_model(normalized_name):
                        elapsed_time = time.time() - start_time
                        logger.info(f"Model {normalized_name} successfully loaded in {elapsed_time:.2f} seconds")
                        return {"status": "success", "elapsed_seconds": elapsed_time}
                    
                    if attempt < max_retries - 1:
                        logger.warning("Model not ready, retrying load operation")
                        continue
                    
                    raise ModelError("Model failed to become ready after loading", "wait")
                    
                except ModelError:
                    raise
                except Exception as e:
                    logger.error(f"Load attempt {attempt+1} failed: {str(e)}")
                    if attempt < max_retries - 1:
                        logger.info(f"Retrying in {MODEL_LOAD_RETRY_DELAY} seconds")
                        await asyncio.sleep(MODEL_LOAD_RETRY_DELAY)
                    else:
                        raise ModelError(f"All {max_retries} load attempts failed: {str(e)}", "load")
            
            # This should not be reached if max_retries > 0
            raise ModelError("Failed to load model after all retries", "load")
            
        except ModelError:
            # Re-raise ModelError
            raise
        except Exception as e:
            logger.exception(f"Unexpected error loading model: {str(e)}")
            raise ModelError(str(e), "unknown")
        finally:
            # Log memory usage after model loading (useful for Jetson optimization)
            try:
                import psutil
                process = psutil.Process(os.getpid())
                memory_info = process.memory_info()
                logger.info(f"Memory usage after model load: {memory_info.rss / (1024 * 1024):.2f} MB")
            except ImportError:
                logger.debug("psutil not available, skipping memory logging")
            except Exception as e:
                logger.debug(f"Failed to log memory usage: {str(e)}")

    async def unload_model(self, name: str) -> Dict[str, str]:
        """Unload a model from Ollama."""
        normalized_name = self.normalize_model_name(name)
        logger.info(f"Unloading model {normalized_name}")
        
        try:
            response = await self.client.delete(
                "/api/delete",
                json={"name": normalized_name}
            )
            
            if response.status_code >= 400:
                error_text = await response.text()
                logger.error(f"Unload failed with status {response.status_code}: {error_text}")
                return {"status": "error", "message": error_text}
            
            logger.info(f"Model {normalized_name} successfully unloaded")
            return {"status": "success"}
        except Exception as e:
            logger.error(f"Error unloading model: {str(e)}")
            return {"status": "error", "message": str(e)}