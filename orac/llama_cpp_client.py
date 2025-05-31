"""
orac.llama_cpp_client
--------------------
A lightweight Python wrapper around the llama.cpp command-line tools that provides:
- Direct model loading and inference
- Support for specialized models like Qwen3
- Seamless integration with ORAC's existing architecture
- Support for model quantization and fine-tuning

This client uses a persistent server model for efficient inference,
with automatic server management and transparent HTTP API usage.
"""

import os
import json
import asyncio
import subprocess
import aiohttp
import weakref
import signal
import psutil
from typing import List, Dict, Any, Optional, Set
from pathlib import Path
from dataclasses import dataclass
from contextlib import asynccontextmanager

from orac.logger import get_logger
from orac.models import PromptResponse
from orac.config import load_model_configs

# JSON grammar for structured output
JSON_GRAMMAR = r'''
root ::= object
object ::= "{" ws (string ":" ws value ("," ws string ":" ws value)*)? ws "}"
value ::= object | array | string | number | boolean | null
array ::= "[" ws (value ("," ws value)*)? ws "]"
string ::= "\"" ([^"\\] | "\\" (["\\/bfnrt] | "u" [0-9a-fA-F] [0-9a-fA-F] [0-9a-fA-F] [0-9a-fA-F]))* "\""
number ::= "-"? ([0-9] | [1-9] [0-9]*) ("." [0-9]+)? ([eE] [-+]? [0-9]+)?
boolean ::= "true" | "false"
null ::= "null" 
ws ::= [ \t\n\r]*
'''

# Get logger for this module
logger = get_logger(__name__)

# Path constants
LLAMA_CPP_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "third_party/llama_cpp")
LLAMA_CLI = os.path.join(LLAMA_CPP_PATH, "bin/llama-cli")
LLAMA_SERVER = os.path.join(LLAMA_CPP_PATH, "bin/llama-server")
# Use environment variable with fallback to relative path for development
MODELS_PATH = os.getenv("ORAC_MODELS_PATH", os.path.join(os.path.dirname(os.path.dirname(__file__)), "models/gguf"))

# Default server settings
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8080
DEFAULT_TIMEOUT = 30

@dataclass
class ServerState:
    """Internal state for a running server instance."""
    process: subprocess.Popen
    host: str
    port: int
    model: str
    session: Optional[aiohttp.ClientSession] = None
    last_used: float = 0.0

class LlamaCppClient:
    """Client for interacting with llama.cpp binaries."""
    
    # Class-level tracking of all client instances and their servers
    _instances: Set[weakref.ReferenceType['LlamaCppClient']] = set()
    _server_ports: Set[int] = set()
    
    def __init__(self, models_path: str = None):
        """
        Initialize the llama.cpp client.
        
        Args:
            models_path: Optional path to models directory. Defaults to MODELS_PATH.
        """
        self.models_path = models_path or MODELS_PATH
        logger.info(f"Initializing LlamaCppClient with models path: {self.models_path}")
        
        # Internal state
        self._servers: Dict[str, ServerState] = {}  # model -> server state
        self._session: Optional[aiohttp.ClientSession] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()
        
        # Ensure the binaries are executable
        for binary in [LLAMA_CLI, LLAMA_SERVER]:
            if os.path.exists(binary) and not os.access(binary, os.X_OK):
                os.chmod(binary, 0o755)
                logger.info(f"Made {binary} executable")
        
        # Set up environment to find shared libraries
        self.env = os.environ.copy()
        self.env["LD_LIBRARY_PATH"] = f"{os.path.join(LLAMA_CPP_PATH, 'lib')}:{self.env.get('LD_LIBRARY_PATH', '')}"
        
        # Verify binaries exist
        if not os.path.exists(LLAMA_CLI):
            raise RuntimeError(f"llama-cli binary not found at {LLAMA_CLI}")
        if not os.path.exists(LLAMA_SERVER):
            raise RuntimeError(f"llama-server binary not found at {LLAMA_SERVER}")
        
        # Register this instance for cleanup
        self._instances.add(weakref.ref(self, self._cleanup_instance))
        
        # Start cleanup task if not already running
        if not any(hasattr(inst(), '_cleanup_task') and inst()._cleanup_task for inst in self._instances if inst()):
            self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
        
        logger.info("LlamaCppClient initialized successfully")

    def __del__(self):
        """Clean up resources when the client is destroyed."""
        try:
            # Signal the cleanup task to stop
            if hasattr(self, '_shutdown_event'):
                self._shutdown_event.set()
            
            # Stop all servers
            for model in list(self._servers.keys()):
                try:
                    server = self._servers[model]
                    if server.process and server.process.poll() is None:
                        server.process.terminate()
                        try:
                            server.process.wait(timeout=1)
                        except subprocess.TimeoutExpired:
                            server.process.kill()
                    
                    # Close session in a new event loop if needed
                    if server.session and not server.session.closed:
                        try:
                            loop = asyncio.get_event_loop()
                            if loop.is_running():
                                asyncio.create_task(server.session.close())
                            else:
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                                loop.run_until_complete(server.session.close())
                                loop.close()
                        except Exception as e:
                            logger.error(f"Error closing server session: {str(e)}")
                    
                    if self._session and not self._session.closed:
                        try:
                            loop = asyncio.get_event_loop()
                            if loop.is_running():
                                asyncio.create_task(self._session.close())
                            else:
                                loop = asyncio.new_event_loop()
                                asyncio.set_event_loop(loop)
                                loop.run_until_complete(self._session.close())
                                loop.close()
                        except Exception as e:
                            logger.error(f"Error closing main session: {str(e)}")
                    
                    self._server_ports.discard(server.port)
                    del self._servers[model]
                except Exception as e:
                    logger.error(f"Error cleaning up server for model {model}: {str(e)}")
            
            # Cancel the cleanup task
            if self._cleanup_task and not self._cleanup_task.done():
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        self._cleanup_task.cancel()
                    else:
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        loop.run_until_complete(self._cleanup_task.cancel())
                        loop.close()
                except Exception as e:
                    logger.error(f"Error cancelling cleanup task: {str(e)}")
        except Exception as e:
            logger.error(f"Error in __del__: {str(e)}")

    @classmethod
    def _cleanup_instance(cls, ref):
        """Clean up when a client instance is destroyed."""
        cls._instances.discard(ref)
        if not cls._instances:
            # No more instances, clean up ports
            cls._server_ports.clear()

    async def _periodic_cleanup(self):
        """Periodically clean up unused servers."""
        try:
            while not self._shutdown_event.is_set():
                current_time = asyncio.get_event_loop().time()
                for model, server in list(self._servers.items()):
                    if current_time - server.last_used > 300:  # 5 minutes
                        try:
                            await self._stop_server(model)
                        except Exception as e:
                            logger.error(f"Error cleaning up server for model {model}: {str(e)}")
                await asyncio.sleep(60)  # Check every minute
        except asyncio.CancelledError:
            # Ensure we clean up any remaining servers on cancellation
            for model in list(self._servers.keys()):
                try:
                    await self._stop_server(model)
                except Exception as e:
                    logger.error(f"Error cleaning up server during shutdown: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"Error in periodic cleanup: {str(e)}")
            raise

    async def _stop_server(self, model: str):
        """Stop a server instance."""
        if model in self._servers:
            server = self._servers[model]
            try:
                if server.process and server.process.poll() is None:
                    server.process.terminate()
                    try:
                        server.process.wait(timeout=1)
                    except subprocess.TimeoutExpired:
                        server.process.kill()
                
                if server.session and not server.session.closed:
                    await server.session.close()
                
                self._server_ports.discard(server.port)
                del self._servers[model]
            except Exception as e:
                logger.error(f"Error stopping server for model {model}: {str(e)}")
                raise

    async def list_models(self) -> List[Dict[str, Any]]:
        """
        List available GGUF models in the models directory.
        
        Returns:
            List of model information dictionaries
        """
        models = []
        
        if os.path.exists(self.models_path):
            for file in os.listdir(self.models_path):
                if file.endswith(".gguf"):
                    model_path = os.path.join(self.models_path, file)
                    models.append({
                        "name": file,
                        "size": os.path.getsize(model_path),
                        "modified": os.path.getmtime(model_path),
                        "backend": "llama_cpp"
                    })
        
        logger.info(f"Found {len(models)} models")
        return models

    async def _ensure_server_running(
        self,
        model: str,
        temperature: float = 0.7,
        top_p: float = 0.7,
        top_k: int = 40,
        json_mode: bool = False
    ) -> ServerState:
        """
        Ensure a server is running for the given model.
        
        Args:
            model: Model name
            temperature: Sampling temperature
            top_p: Top-p sampling parameter
            top_k: Top-k sampling parameter
            json_mode: Whether to enforce JSON grammar
            
        Returns:
            ServerState for the running server
        """
        # Check if we already have a server for this model
        if model in self._servers:
            server = self._servers[model]
            if server.process.poll() is None:  # Server is still running
                server.last_used = asyncio.get_event_loop().time()
                return server
            else:
                # Server died, clean it up
                await self._stop_server(model)
        
        # Find an available port
        port = DEFAULT_PORT
        while port in self._server_ports:
            port += 1
        
        # Start a new server
        server = await self._start_internal_server(
            model=model,
            host=DEFAULT_HOST,
            port=port,
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
            json_mode=json_mode
        )
        
        self._servers[model] = server
        self._server_ports.add(port)
        return server

    async def _start_internal_server(
        self,
        model: str,
        host: str,
        port: int,
        temperature: float = 0.7,
        top_p: float = 0.7,
        top_k: int = 40,
        json_mode: bool = False
    ) -> ServerState:
        """
        Start a new server instance.
        
        Args:
            model: Model name
            host: Server host
            port: Server port
            temperature: Sampling temperature
            top_p: Top-p sampling parameter
            top_k: Top-k sampling parameter
            json_mode: Whether to enforce JSON grammar
            
        Returns:
            ServerState for the new server
        """
        model_path = os.path.join(self.models_path, model)
        if not model_path.endswith(".gguf"):
            model_path += ".gguf"
            
        if not os.path.exists(model_path):
            raise FileNotFoundError(f"Model not found: {model_path}")
        
        cmd = [
            LLAMA_SERVER,
            "-m", model_path,
            "--host", host,
            "--port", str(port),
            "--temp", str(temperature),
            "--top-p", str(top_p),
            "--top-k", str(top_k)
        ]
        
        # Only add grammar if json_mode is True
        if json_mode:
            cmd.extend(["--grammar", JSON_GRAMMAR.strip()])
        
        # Start the server process
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=self.env
        )
        
        # Wait for server to start
        for _ in range(10):  # Try for 5 seconds
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"http://{host}:{port}/health") as response:
                        if response.status == 200:
                            # Create a new session for this server
                            server_session = aiohttp.ClientSession(
                                base_url=f"http://{host}:{port}",
                                timeout=aiohttp.ClientTimeout(total=DEFAULT_TIMEOUT)
                            )
                            return ServerState(
                                process=process,
                                host=host,
                                port=port,
                                model=model,
                                session=server_session,
                                last_used=asyncio.get_event_loop().time()
                            )
            except Exception:
                pass
            await asyncio.sleep(0.5)
        
        # If we get here, server didn't start
        process.terminate()
        stdout, stderr = process.communicate()
        error = stderr.decode('utf-8', errors='replace')
        raise Exception(f"Failed to start llama server: {error}")

    @asynccontextmanager
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create an aiohttp session."""
        if not self._session:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=DEFAULT_TIMEOUT)
            )
        try:
            yield self._session
        except Exception as e:
            logger.error(f"Session error: {e}")
            if self._session:
                await self._session.close()
                self._session = None
            raise

    async def generate(
        self,
        prompt: str,
        model: str,
        temperature: float = 0.7,
        top_p: float = 0.7,
        top_k: int = 40,
        max_tokens: Optional[int] = None,
        verbose: bool = False,
        timeout: int = 30,
        system_prompt: Optional[str] = None,
        json_mode: bool = False
    ) -> PromptResponse:
        """
        Generate a response from the model.
        
        Args:
            model: Model name
            prompt: Text prompt
            stream: Whether to stream the response
            temperature: Sampling temperature
            top_p: Top-p sampling parameter
            top_k: Top-k sampling parameter
            max_tokens: Maximum tokens to generate
            verbose: Whether to run in verbose mode
            timeout: Maximum time in seconds to wait for generation
            system_prompt: Optional system prompt to override the model's default
            json_mode: Whether to enforce JSON grammar
            
        Returns:
            PromptResponse with generated text and metadata
        """
        if not prompt.strip():
            raise ValueError("Prompt cannot be empty")

        start_time = asyncio.get_event_loop().time()
        
        try:
            # Load model configuration
            model_configs = load_model_configs()
            model_config = model_configs.get("models", {}).get(model, {})
            
            # Get the prompt format template and system prompt
            prompt_format = model_config.get("prompt_format", {})
            template = prompt_format.get("template", "{system_prompt}\n\n{user_prompt}")
            default_system_prompt = model_config.get("system_prompt", "")
            
            # Use provided system prompt or fall back to model's default
            system_prompt = system_prompt or default_system_prompt
            
            # Format the prompt using the template
            formatted_prompt = template.format(
                system_prompt=system_prompt,
                user_prompt=prompt
            )
            
            # Get model's recommended settings
            recommended_settings = model_config.get("recommended_settings", {})
            temperature = temperature if temperature != 0.7 else recommended_settings.get("temperature", temperature)
            top_p = top_p if top_p != 0.7 else recommended_settings.get("top_p", top_p)
            top_k = top_k if top_k != 40 else recommended_settings.get("top_k", top_k)
            max_tokens = max_tokens or recommended_settings.get("max_tokens", 512)
            
            # Ensure we have a server running for this model
            server = await self._ensure_server_running(
                model=model,
                temperature=temperature,
                top_p=top_p,
                top_k=top_k,
                json_mode=json_mode
            )
            
            # Prepare request data
            request_data = {
                "prompt": formatted_prompt,
                "temperature": temperature,
                "top_p": top_p,
                "top_k": top_k,
                "max_tokens": max_tokens
            }
            
            # Only include grammar in request if json_mode is True
            if json_mode:
                request_data["grammar"] = JSON_GRAMMAR.strip()
            
            # Make request to server
            async with self._get_session() as session:
                async with session.post(
                    f"http://{server.host}:{server.port}/completion",
                    json=request_data
                ) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        raise Exception(f"Server error: {error_text}")
                    
                    result = await response.json()
                    response_text = result.get("content", "")
                    
                    # Clean up the response
                    response_text = response_text.strip()
                    
                    # Remove any remaining markers
                    for marker in ["<|im_end|>", "<|im_start|>", "<think>", "</think>"]:
                        response_text = response_text.replace(marker, "")
                    
                    # Clean up whitespace
                    response_text = ' '.join(response_text.split())
                    
                    if not response_text:
                        logger.warning("Empty response from model")
                        response_text = "No response generated"
                    
                    return PromptResponse(
                        text=response_text,
                        model=model,
                        temperature=temperature,
                        top_p=top_p,
                        top_k=top_k,
                        max_tokens=max_tokens,
                        json_mode=json_mode,
                        system_prompt=system_prompt,
                        prompt=prompt,
                        generated_at=start_time,
                        response_time=asyncio.get_event_loop().time() - start_time
                    )
                    
        except Exception as e:
            logger.error(f"Generation error: {str(e)}")
            raise

    async def start_server(
        self,
        model: str,
        host: str = "127.0.0.1",
        port: int = 8080,
        temperature: float = 0.7,
        top_p: float = 0.7,
        top_k: int = 40
    ) -> subprocess.Popen:
        """
        Start the llama.cpp server with the specified model.
        
        This method maintains backward compatibility by returning a subprocess.Popen
        object, but internally uses the new server management system.
        
        Args:
            model: Model name
            host: Server host
            port: Server port
            temperature: Sampling temperature
            top_p: Top-p sampling parameter
            top_k: Top-k sampling parameter
            
        Returns:
            Subprocess handle for the server process
        """
        # Check if we already have a server for this model
        if model in self._servers:
            server = self._servers[model]
            if server.process.poll() is None:  # Server is still running
                if server.host == host and server.port == port:
                    # Server is already running on the requested host/port
                    return server.process
                else:
                    # Server is running but on different host/port
                    await self._stop_server(model)
            else:
                # Server died, clean it up
                await self._stop_server(model)
        
        # Start a new server
        server = await self._start_internal_server(
            model=model,
            host=host,
            port=port,
            temperature=temperature,
            top_p=top_p,
            top_k=top_k
        )
        
        self._servers[model] = server
        self._server_ports.add(port)
        
        # Return the process handle for backward compatibility
        return server.process

    async def quantize_model(
        self,
        input_model: str,
        output_model: str,
        quantization_type: str = "q4_k"
    ) -> bool:
        """
        Quantize a model to a specific format.
        
        Args:
            input_model: Input model name
            output_model: Output model name
            quantization_type: Quantization type (e.g., q4_k)
            
        Returns:
            True if quantization was successful
        """
        input_path = os.path.join(self.models_path, input_model)
        if not input_path.endswith(".gguf"):
            input_path += ".gguf"
            
        output_path = os.path.join(self.models_path, output_model)
        if not output_path.endswith(".gguf"):
            output_path += ".gguf"
        
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input model not found: {input_path}")
        
        cmd = [
            os.path.join(LLAMA_CPP_PATH, "bin/llama-quantize"),
            input_path,
            output_path,
            quantization_type
        ]
        
        process = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=self.env
        )
        
        stdout, stderr = await process.communicate()
        
        if process.returncode != 0:
            error = stderr.decode('utf-8', errors='replace')
            raise Exception(f"Quantization error: {error}")
        
        success = os.path.exists(output_path)
        if success:
            logger.info(f"Successfully quantized model to {output_path}")
        return success 