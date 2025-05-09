"""
orac.ollama_client
------------------
A thin async wrapper around the Ollama REST API, optimized for Jetson Orin Nano.

Key features:
- Async HTTP client using httpx
- Memory-efficient generation
- Robust error handling and retries
- Streaming support with memory management
- Resource monitoring for Jetson platforms
"""

import os
import json
import time
import asyncio
from typing import Dict, List, Any, Optional, AsyncGenerator

import httpx
from orac.logger import get_logger
from orac.model_loader import ModelLoader, ModelError

# Environment configuration
OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "127.0.0.1")
OLLAMA_PORT = os.environ.get("OLLAMA_PORT", "11434")
OLLAMA_BASE_URL = f"http://{OLLAMA_HOST}:{OLLAMA_PORT}"

# Generation parameters - configurable via environment
DEFAULT_TEMPERATURE = float(os.environ.get("DEFAULT_TEMPERATURE", "0.7"))
DEFAULT_TOP_P = float(os.environ.get("DEFAULT_TOP_P", "0.7"))
DEFAULT_TOP_K = int(os.environ.get("DEFAULT_TOP_K", "40"))
GENERATION_TIMEOUT = float(os.environ.get("GENERATION_TIMEOUT", "120.0"))

# Get logger for this module
logger = get_logger(__name__)


class OllamaClient:
    """Client for interacting with Ollama API, optimized for Jetson platforms."""
    
    def __init__(self, base_url: str = None):
        """
        Initialize the Ollama client.
        
        Args:
            base_url: The base URL for the Ollama API. If None, uses environment variables.
        """
        self.base_url = base_url or OLLAMA_BASE_URL
        logger.info(f"Initializing OllamaClient with base URL: {self.base_url}")
        
        # Configure client with default timeouts
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=60.0  # Default timeout for regular operations
        )
        
        # Create model loader
        self.model_loader = ModelLoader(self.client)
    
    async def get_version(self) -> str:
        """
        Get the Ollama version.
        
        Returns:
            str: The version string
        """
        try:
            response = await self.client.get("/api/version")
            response.raise_for_status()
            version = response.json().get("version", "unknown")
            logger.info(f"Ollama version: {version}")
            return version
        except Exception as e:
            logger.error(f"Failed to get Ollama version: {str(e)}")
            return "unknown"
    
    async def list_models(self) -> List[Dict[str, Any]]:
        """
        List all available models.
        
        Returns:
            List[Dict[str, Any]]: List of model information dictionaries
        """
        try:
            logger.debug("Listing models")
            response = await self.client.get("/api/tags")
            response.raise_for_status()
            models = response.json().get("models", [])
            logger.info(f"Found {len(models)} models")
            return models
        except Exception as e:
            logger.error(f"Error listing models: {str(e)}")
            raise Exception(f"Failed to list models: {str(e)}")
    
    async def load_model(self, name: str, max_retries: int = 3) -> Dict[str, Any]:
        """
        Load a model by name.
        
        Args:
            name: The model name
            max_retries: Maximum number of retries
        
        Returns:
            Dict[str, Any]: Status response
        """
        logger.info(f"Loading model: {name} (max_retries={max_retries})")
        try:
            start_time = time.time()
            result = await self.model_loader.load_model(name, max_retries)
            elapsed = time.time() - start_time
            logger.info(f"Model {name} loaded in {elapsed:.2f}s")
            return {"status": "success", "elapsed_seconds": elapsed}
        except ModelError as e:
            logger.error(f"ModelError: {e.stage} - {e.message}")
            return {"status": "error", "stage": e.stage, "message": e.message}
        except Exception as e:
            logger.exception(f"Unexpected error loading model: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    async def unload_model(self, name: str) -> Dict[str, Any]:
        """
        Unload a model by name.
        
        Args:
            name: The model name
        
        Returns:
            Dict[str, Any]: Status response
        """
        logger.info(f"Unloading model: {name}")
        try:
            result = await self.model_loader.unload_model(name)
            return result
        except Exception as e:
            logger.error(f"Error unloading model: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    async def generate(
        self,
        model: str,
        prompt: str,
        temperature: float = DEFAULT_TEMPERATURE,
        top_p: float = DEFAULT_TOP_P,
        top_k: int = DEFAULT_TOP_K,
        stream: bool = False,
        stop: List[str] = None,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Generate a response from the model.
        
        Args:
            model: Model name
            prompt: Text prompt
            temperature: Sampling temperature (0.0 to 1.0)
            top_p: Top-p sampling parameter
            top_k: Top-k sampling parameter
            stream: Whether to stream the response
            stop: List of stop sequences
            max_tokens: Maximum tokens to generate
            
        Returns:
            Dict[str, Any]: Response information including the generated text
        """
        if not prompt or not prompt.strip():
            logger.error("Empty prompt provided")
            raise ValueError("Prompt cannot be empty")
        
        # Normalize model name
        model_name = self.model_loader.normalize_model_name(model)
        logger.info(f"Generating with model: {model_name} (stream={stream})")
        logger.debug(f"Prompt: {prompt[:100]}...")  # Log beginning of prompt
        
        # Memory monitoring for Jetson platform
        try:
            self._log_memory_usage("before_generation")
        except Exception as e:
            logger.debug(f"Memory monitoring error: {str(e)}")
        
        start_time = time.time()
        
        # Prepare generation parameters - use Jetson-optimized defaults
        params = {
            "model": model_name,
            "prompt": prompt,
            "stream": stream,
            "temperature": temperature,
            "top_p": top_p,
            "top_k": top_k,
        }
        
        # Add optional parameters
        if stop:
            params["stop"] = stop
        if max_tokens:
            params["max_tokens"] = max_tokens
        
        try:
            if stream:
                return await self._generate_stream(params)
            else:
                return await self._generate_complete(params)
        except Exception as e:
            logger.error(f"Generation error: {str(e)}")
            return {
                "status": "error",
                "message": str(e),
                "elapsed_ms": (time.time() - start_time) * 1000
            }
    
    def _log_memory_usage(self, stage: str) -> None:
        """Log memory usage - useful for Jetson optimization."""
        try:
            import psutil
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            
            # Get system memory info too
            system_memory = psutil.virtual_memory()
            
            logger.info(
                f"Memory at {stage}: "
                f"Process: {memory_info.rss / (1024*1024):.2f} MB, "
                f"System: {system_memory.used / (1024*1024):.2f} MB / "
                f"{system_memory.total / (1024*1024):.2f} MB "
                f"({system_memory.percent:.1f}%)"
            )
        except ImportError:
            logger.debug("psutil not available, skipping memory monitoring")
        except Exception as e:
            logger.debug(f"Failed to log memory usage: {str(e)}")
    
    async def pull_model(self, name: str) -> Dict[str, Any]:
        """
        Pull a model from Ollama library.
        
        Args:
            name: Model name to pull
            
        Returns:
            Dict[str, Any]: Status and information
        """
        logger.info(f"Pulling model: {name}")
        start_time = time.time()
        
        try:
            response = await self.client.post(
                "/api/pull",
                json={"name": name},
                timeout=None  # No timeout for pulls as they can take a long time
            )
            response.raise_for_status()
            
            result = response.json()
            elapsed = time.time() - start_time
            
            logger.info(f"Model {name} pulled in {elapsed:.2f}s")
            return {
                "status": "success",
                "elapsed_seconds": elapsed,
                "model": name
            }
        except httpx.HTTPStatusError as e:
            try:
                error_data = e.response.json()
                error_message = error_data.get("error", str(e))
            except:
                error_message = f"HTTP error {e.response.status_code}: {str(e)}"
            
            logger.error(f"Failed to pull model: {error_message}")
            return {
                "status": "error",
                "message": error_message,
                "elapsed_seconds": time.time() - start_time
            }
        except Exception as e:
            logger.exception(f"Unexpected error pulling model: {str(e)}")
            return {
                "status": "error", 
                "message": str(e),
                "elapsed_seconds": time.time() - start_time
            }
    
    async def show_model(self, name: str) -> Dict[str, Any]:
        """
        Get information about a model.
        
        Args:
            name: Model name
            
        Returns:
            Dict[str, Any]: Model information
        """
        model_name = self.model_loader.normalize_model_name(name)
        logger.info(f"Getting info for model: {model_name}")
        
        try:
            response = await self.client.post(
                "/api/show",
                json={"name": model_name}
            )
            
            if response.status_code == 404:
                logger.info(f"Model {model_name} not found")
                return {"status": "error", "message": "Model not found"}
            
            response.raise_for_status()
            result = response.json()
            
            logger.info(f"Got info for model: {model_name}")
            return {
                "status": "success",
                "model": result
            }
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error getting model info: {str(e)}")
            return {"status": "error", "message": str(e)}
        except Exception as e:
            logger.error(f"Error getting model info: {str(e)}")
            return {"status": "error", "message": str(e)}
    
    async def close(self):
        """Close the HTTP client and clean up resources."""
        logger.info("Closing OllamaClient and releasing resources")
        await self.client.aclose()
    
    async def _generate_complete(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a complete response (non-streaming)."""
        start_time = time.time()
        
        try:
            # Create a new client with generation-specific timeout
            async with httpx.AsyncClient(
                base_url=self.base_url,
                timeout=GENERATION_TIMEOUT
            ) as generation_client:
                logger.debug(f"Sending generation request with params: {json.dumps(params)}")
                response = await generation_client.post("/api/generate", json=params)
                response.raise_for_status()
                
                result = response.json()
                elapsed_ms = (time.time() - start_time) * 1000
                
                # Monitor memory after generation
                self._log_memory_usage("after_generation")
                
                logger.info(f"Generation completed in {elapsed_ms:.2f}ms")
                logger.debug(f"Generated text: {result.get('response', '')[:100]}...")
                
                return {
                    "status": "success",
                    "response": result.get("response", ""),
                    "elapsed_ms": elapsed_ms
                }
        except httpx.HTTPStatusError as e:
            try:
                error_data = e.response.json()
                error_message = error_data.get("error", str(e))
            except:
                error_message = f"HTTP error {e.response.status_code}: {str(e)}"
            
            logger.error(f"HTTP error during generation: {error_message}")
            return {
                "status": "error",
                "message": error_message,
                "elapsed_ms": (time.time() - start_time) * 1000
            }
        except Exception as e:
            logger.exception(f"Unexpected error during generation: {str(e)}")
            return {
                "status": "error",
                "message": str(e),
                "elapsed_ms": (time.time() - start_time) * 1000
            }
    
    async def _generate_stream(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Generate a streaming response and collect results."""
        start_time = time.time()
        full_response = ""
        
        try:
            # Use a dedicated client for streaming with appropriate timeout
            async with httpx.AsyncClient(
                base_url=self.base_url,
                timeout=GENERATION_TIMEOUT
            ) as streaming_client:
                logger.debug(f"Sending streaming generation request with params: {json.dumps(params)}")
                
                async with streaming_client.stream(
                    "POST",
                    "/api/generate",
                    json=params
                ) as response:
                    response.raise_for_status()
                    
                    # Process streaming response
                    async for line in response.aiter_lines():
                        if not line:
                            continue
                        
                        try:
                            chunk = json.loads(line)
                            chunk_text = chunk.get("response", "")
                            full_response += chunk_text
                            
                            # If done is present and true, break
                            if chunk.get("done", False):
                                break
                        except json.JSONDecodeError:
                            logger.warning(f"Failed to parse JSON line: {line}")
                            continue
            
            elapsed_ms = (time.time() - start_time) * 1000
            
            # Monitor memory after streaming
            self._log_memory_usage("after_streaming")
            
            logger.info(f"Streaming generation completed in {elapsed_ms:.2f}ms")
            logger.debug(f"Total generated text: {len(full_response)} characters")
            
            return {
                "status": "success",
                "response": full_response,
                "elapsed_ms": elapsed_ms
            }
        except httpx.HTTPStatusError as e:
            try:
                error_data = e.response.json()
                error_message = error_data.get("error", str(e))
            except:
                error_message = f"HTTP error {e.response.status_code}: {str(e)}"
            
            logger.error(f"HTTP error during streaming: {error_message}")
            return {
                "status": "error",
                "message": error_message,
                "elapsed_ms": (time.time() - start_time) * 1000
            }
        except Exception as e:
            logger.exception(f"Unexpected error during streaming: {str(e)}")
            return {
                "status": "error",
                "message": str(e),
                "elapsed_ms": (time.time() - start_time) * 1000
            }
            