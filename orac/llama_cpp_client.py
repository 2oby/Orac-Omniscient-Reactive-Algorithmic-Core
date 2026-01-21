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
import yaml
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

# Orin Nano optimizations (configurable via environment)
ORIN_NANO_OPTIMIZATIONS = os.getenv("ORAC_ORIN_OPTIMIZATIONS", "true").lower() == "true"
ORIN_CTX_SIZE = os.getenv("ORAC_CTX_SIZE", "2048")
ORIN_GPU_LAYERS = os.getenv("ORAC_GPU_LAYERS", "999")

@dataclass
class ServerState:
    """Internal state for a running server instance."""
    process: subprocess.Popen
    host: str
    port: int
    model: str
    session: Optional[aiohttp.ClientSession] = None
    last_used: float = 0.0
    grammar_file: Optional[str] = None  # Track grammar to avoid unnecessary restarts
    pre_warmed: bool = False  # Whether KV cache has been pre-warmed with system prompt
    consecutive_failures: int = 0  # Health check failure counter
    last_health_check: Optional[float] = None  # Timestamp of last health check
    restart_count: int = 0  # Number of times server was restarted

class LlamaCppClient:
    """Client for interacting with llama.cpp binaries."""
    
    # Class-level tracking of all client instances and their servers
    _instances: Set[weakref.ReferenceType['LlamaCppClient']] = set()
    _server_ports: Set[int] = set()
    # Class-level cache for grammars
    _grammars: Optional[Dict[str, Dict[str, Any]]] = None
    # Class-level cache for model configurations
    _model_configs: Optional[Dict[str, Any]] = None
    # Class-level cache for system prompts
    _system_prompts: Dict[str, str] = {
        "json": """You must respond with valid JSON only. Do not include any explanations, thinking, or commentary outside the JSON structure. Your response should be clean, properly formatted JSON that directly answers the request."""
    }
    
    def __init__(self, model_path: str, config_path: str = "data/model_configs.yaml"):
        """Initialize the LlamaCppClient with model and configuration paths."""
        self.model_path = model_path
        self.config_path = config_path
        self.model = None
        self.config = self._load_config()
        
        # Load grammars only once at class level
        if LlamaCppClient._grammars is None:
            LlamaCppClient._grammars = self._load_grammars()
        self.grammars = LlamaCppClient._grammars
        
        # Load model configs only once at class level
        if LlamaCppClient._model_configs is None:
            LlamaCppClient._model_configs = load_model_configs()
        self.model_configs = LlamaCppClient._model_configs
        
        logger.info(f"Initializing LlamaCppClient with models path: {self.model_path}")
        
        # Internal state
        self._servers: Dict[str, ServerState] = {}  # model -> server state
        self._session: Optional[aiohttp.ClientSession] = None
        self._cleanup_task: Optional[asyncio.Task] = None
        self._shutdown_event = asyncio.Event()

        # Health monitoring settings
        self._health_check_timeout = 5.0  # seconds
        self._max_consecutive_failures = 2  # restart after this many failures
        self._total_restart_count = 0  # total restarts across all models
        
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
            
            # Only try to clean up servers if _servers was initialized
            if not hasattr(self, '_servers'):
                return
                
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
            if hasattr(self, '_cleanup_task') and self._cleanup_task and not self._cleanup_task.done():
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

    async def _check_server_health(self, model: str, server: ServerState) -> bool:
        """Check if a server is healthy by pinging its /health endpoint.

        Args:
            model: Model name
            server: Server state

        Returns:
            True if server is healthy, False otherwise
        """
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"http://{server.host}:{server.port}/health",
                    timeout=aiohttp.ClientTimeout(total=self._health_check_timeout)
                ) as response:
                    if response.status == 200:
                        health_data = await response.json()
                        status = health_data.get("status", "")
                        if status == "ok":
                            return True
                        elif "loading" in status.lower():
                            # Model loading, consider healthy
                            return True
            return False
        except asyncio.TimeoutError:
            logger.warning(f"Health check timed out for model {model} on port {server.port}")
            return False
        except Exception as e:
            logger.warning(f"Health check failed for model {model}: {e}")
            return False

    async def _periodic_cleanup(self):
        """Periodically clean up unused servers and check health."""
        try:
            while not self._shutdown_event.is_set():
                current_time = asyncio.get_event_loop().time()
                for model, server in list(self._servers.items()):
                    # Check if server process is still running
                    if server.process.poll() is not None:
                        exit_code = server.process.poll()
                        logger.warning(f"Server for model {model} died (exit code: {exit_code})")
                        await self._stop_server(model)
                        continue

                    # Perform health check
                    server.last_health_check = current_time
                    healthy = await self._check_server_health(model, server)

                    if not healthy:
                        server.consecutive_failures += 1
                        logger.warning(
                            f"llama-server health check failed for {model} "
                            f"({server.consecutive_failures}/{self._max_consecutive_failures})"
                        )

                        if server.consecutive_failures >= self._max_consecutive_failures:
                            logger.error(
                                f"llama-server for {model} unresponsive for "
                                f"{server.consecutive_failures} checks, restarting..."
                            )
                            # Store grammar file for restart
                            grammar_file = server.grammar_file
                            await self._stop_server(model)

                            # Restart the server
                            try:
                                new_server = await self._start_internal_server(
                                    model=model,
                                    host=DEFAULT_HOST,
                                    port=self._find_available_port(),
                                    grammar_file=grammar_file
                                )
                                new_server.restart_count = server.restart_count + 1
                                self._servers[model] = new_server
                                self._server_ports.add(new_server.port)
                                self._total_restart_count += 1
                                logger.info(
                                    f"llama-server for {model} restarted successfully "
                                    f"(restart #{new_server.restart_count})"
                                )
                            except Exception as e:
                                logger.error(f"Failed to restart llama-server for {model}: {e}")
                    else:
                        if server.consecutive_failures > 0:
                            logger.info(f"llama-server for {model} recovered")
                        server.consecutive_failures = 0

                    # Clean up unused servers (5 minutes idle)
                    if current_time - server.last_used > 300:
                        try:
                            logger.info(f"Stopping idle server for model {model}")
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

    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of all managed servers.

        Returns:
            Dictionary with health information
        """
        servers_status = []
        total_consecutive_failures = 0

        for model, server in self._servers.items():
            process_running = server.process.poll() is None
            servers_status.append({
                "model": model,
                "port": server.port,
                "process_running": process_running,
                "consecutive_failures": server.consecutive_failures,
                "restart_count": server.restart_count,
                "last_health_check": server.last_health_check,
                "last_used": server.last_used,
            })
            total_consecutive_failures += server.consecutive_failures

        # Determine overall health
        if not self._servers:
            overall_status = "no_servers"
        elif total_consecutive_failures >= self._max_consecutive_failures:
            overall_status = "unhealthy"
        elif total_consecutive_failures > 0:
            overall_status = "degraded"
        else:
            overall_status = "healthy"

        return {
            "status": overall_status,
            "total_restart_count": self._total_restart_count,
            "max_consecutive_failures": self._max_consecutive_failures,
            "servers": servers_status,
        }

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
        
        if os.path.exists(self.model_path):
            for file in os.listdir(self.model_path):
                if file.endswith(".gguf"):
                    model_path = os.path.join(self.model_path, file)
                    models.append({
                        "name": file,
                        "size": os.path.getsize(model_path),
                        "modified": os.path.getmtime(model_path),
                        "backend": "llama_cpp"
                    })
        
        logger.info(f"Found {len(models)} models")
        return models

    def _find_available_port(self) -> int:
        """Find an available port for a new server.
        
        Returns:
            Available port number
        """
        port = DEFAULT_PORT
        while port in self._server_ports:
            port += 1
        return port

    async def _ensure_server_running(
        self,
        model: str,
        temperature: float = 0.7,
        top_p: float = 0.7,
        top_k: int = 40,
        json_mode: bool = True,
        grammar_file: str = None
    ) -> ServerState:
        """
        Ensure a server is running for the specified model.
        
        Args:
            model: Model name
            temperature: Sampling temperature
            top_p: Top-p sampling parameter
            top_k: Top-k sampling parameter
            json_mode: Whether to enforce JSON grammar
            grammar_file: Path to GBNF grammar file (optional)
            
        Returns:
            ServerState for the running server
        """
        # Check if we already have a server for this model
        if model in self._servers:
            server = self._servers[model]
            if server.process.poll() is None:  # Server is still running
                # Only restart if grammar file actually changed
                if grammar_file != server.grammar_file:
                    logger.info(f"Restarting server for model {model}: grammar changed from {server.grammar_file} to {grammar_file}")
                    await self._stop_server(model)
                else:
                    # Reuse existing server - grammar matches
                    server.last_used = asyncio.get_event_loop().time()
                    return server
            else:
                # Server died, clean it up
                exit_code = server.process.poll()
                logger.warning(f"Server for model {model} died (exit code: {exit_code}), restarting...")
                await self._stop_server(model)

        # Find an available port
        port = self._find_available_port()
        
        # Start a new server
        server = await self._start_internal_server(
            model=model,
            host="127.0.0.1",
            port=port,
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
            json_mode=json_mode,
            grammar_file=grammar_file
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
        json_mode: bool = False,
        grammar_file: str = None
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
            grammar_file: Path to GBNF grammar file (optional)
            
        Returns:
            ServerState for the new server
        """
        model_path = os.path.join(self.model_path, model)
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
        
        # Add Orin Nano optimizations if enabled
        if ORIN_NANO_OPTIMIZATIONS:
            cmd.extend(["--ctx-size", ORIN_CTX_SIZE])
            cmd.extend(["--n-gpu-layers", ORIN_GPU_LAYERS])
        
        # Add grammar if specified
        if grammar_file and os.path.exists(grammar_file):
            cmd.extend(["--grammar-file", grammar_file])
        elif json_mode:
            # Fallback to JSON grammar for backward compatibility
            cmd.extend(["--grammar", self.get_grammar('json').strip()])
        
        # Start the server process
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=self.env
        )
        
        # Wait for server to start AND model to load
        # Note: /health returns 200 with {"status":"loading model"} while loading,
        # and {"status":"ok"} when ready
        for attempt in range(30):  # Try for 15 seconds (model loading can take a while)
            try:
                async with aiohttp.ClientSession() as session:
                    async with session.get(f"http://{host}:{port}/health") as response:
                        if response.status == 200:
                            health_data = await response.json()
                            status = health_data.get("status", "")
                            if status == "ok":
                                # Model is fully loaded and ready
                                logger.info(f"Server ready for model {model} on port {port}")
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
                                    last_used=asyncio.get_event_loop().time(),
                                    grammar_file=grammar_file
                                )
                            elif "loading" in status.lower():
                                # Model still loading, wait and retry
                                logger.debug(f"Model still loading on port {port}...")
            except Exception:
                pass
            await asyncio.sleep(0.5)
        
        # If we get here, server didn't start
        process.terminate()
        stdout, stderr = process.communicate()
        error = stderr.decode('utf-8', errors='replace')
        raise Exception(f"Failed to start llama server: {error}")

    async def _prewarm_cache(self, server: ServerState, system_prompt: str) -> bool:
        """
        Pre-warm the KV cache by sending a minimal request with the system prompt.

        This populates the cache with the tokenized system prompt so subsequent
        requests can reuse it, saving ~100ms of prompt processing time.

        Args:
            server: The server state to pre-warm
            system_prompt: The system prompt to cache

        Returns:
            True if pre-warming was successful
        """
        if server.pre_warmed:
            return True

        try:
            # Get model config for prompt template
            model_config = self.model_configs.get("models", {}).get(server.model, {})
            prompt_format = model_config.get("prompt_format", {})
            template = prompt_format.get("template", "{system_prompt}\n\n{user_prompt}")

            # Format a minimal warm-up prompt
            warmup_prompt = template.format(
                system_prompt=system_prompt,
                user_prompt="warmup"  # Minimal user input
            )

            # Send warm-up request with cache_prompt enabled
            warmup_data = {
                "prompt": warmup_prompt,
                "max_tokens": 1,  # Generate minimal tokens
                "temperature": 0.0,
                "cache_prompt": True  # Explicitly enable caching
            }

            logger.info(f"Pre-warming KV cache for model {server.model}...")
            start_time = asyncio.get_event_loop().time()

            # Retry loop to handle "Loading model" 503 errors
            max_retries = 10
            retry_delay = 0.5  # seconds

            async with aiohttp.ClientSession() as session:
                for attempt in range(max_retries):
                    try:
                        async with session.post(
                            f"http://{server.host}:{server.port}/completion",
                            json=warmup_data,
                            timeout=aiohttp.ClientTimeout(total=30)
                        ) as response:
                            if response.status == 200:
                                elapsed = asyncio.get_event_loop().time() - start_time
                                server.pre_warmed = True
                                logger.info(f"KV cache pre-warmed for {server.model} in {elapsed:.3f}s")
                                return True
                            elif response.status == 503:
                                # Model still loading, wait and retry
                                error_text = await response.text()
                                if "Loading model" in error_text and attempt < max_retries - 1:
                                    logger.debug(f"Model still loading, retrying in {retry_delay}s...")
                                    await asyncio.sleep(retry_delay)
                                    continue
                                else:
                                    logger.warning(f"Pre-warm request failed after retries: {error_text}")
                                    return False
                            else:
                                error = await response.text()
                                logger.warning(f"Pre-warm request failed: {error}")
                                return False
                    except asyncio.TimeoutError:
                        if attempt < max_retries - 1:
                            logger.debug(f"Pre-warm timeout, retrying...")
                            await asyncio.sleep(retry_delay)
                            continue
                        raise

            return False

        except Exception as e:
            logger.warning(f"Failed to pre-warm cache: {e}")
            return False

    async def prewarm_kv_cache(self, model: str, system_prompt: str = "") -> bool:
        """
        Public method to pre-warm KV cache for a model.

        Call this after _ensure_server_running() to pre-warm the cache
        before the first actual request. This saves ~200ms on first request.

        Args:
            model: The model name to pre-warm
            system_prompt: Optional system prompt to cache (uses default if empty)

        Returns:
            True if pre-warming was successful
        """
        if model not in self._servers:
            logger.warning(f"Cannot pre-warm cache: no server running for {model}")
            return False

        server = self._servers[model]

        # Use a default grammar-mode system prompt if none provided
        if not system_prompt:
            system_prompt = "/no_think Match input to JSON."

        return await self._prewarm_cache(server, system_prompt)

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
        json_mode: bool = True,
        stream: bool = False,
        grammar_file: str = None
    ) -> PromptResponse:
        """
        Generate a response from the model.
        
        Args:
            model: Model name
            prompt: Text prompt
            temperature: Sampling temperature
            top_p: Top-p sampling parameter
            top_k: Top-k sampling parameter
            max_tokens: Maximum tokens to generate
            verbose: Whether to run in verbose mode
            timeout: Maximum time in seconds to wait for generation
            system_prompt: Optional system prompt to override the model's default
            json_mode: Whether to enforce JSON grammar
            stream: Whether to stream the response (not currently implemented)
            grammar_file: Path to GBNF grammar file (optional)
            
        Returns:
            PromptResponse with generated text and metadata
        """
        if not prompt.strip():
            raise ValueError("Prompt cannot be empty")

        start_time = asyncio.get_event_loop().time()
        
        try:
            # Get model configuration from cache
            model_config = self.model_configs.get("models", {}).get(model, {})
            
            # Get the prompt format template and system prompt
            prompt_format = model_config.get("prompt_format", {})
            template = prompt_format.get("template", "{system_prompt}\n\n{user_prompt}")
            default_system_prompt = model_config.get("system_prompt", "")
            
            # Use JSON-specific system prompt when in JSON mode
            if json_mode:
                system_prompt = self._system_prompts["json"]
            else:
                # Use provided system prompt or fall back to model's default
                system_prompt = system_prompt or default_system_prompt
            
            # Format the prompt using the template
            formatted_prompt = template.format(
                system_prompt=system_prompt,
                user_prompt=prompt
            )
            
            # Get model's recommended settings
            recommended_settings = model_config.get("recommended_settings", {})
            
            # Set parameters based on grammar usage
            if grammar_file or json_mode:
                # Grammar mode: use deterministic temperature, but RESPECT caller's top_p/top_k
                # Only override if caller used default values (0.7/40 = function defaults)
                temperature = 0.0  # Always deterministic for grammar mode
                if top_p == 0.7:  # Caller used default, apply grammar-optimized value
                    top_p = 0.8
                # else: caller passed non-default (e.g., topic's 0.2), respect it
                if top_k == 40:  # Caller used default, apply grammar-optimized value
                    top_k = 30
                # else: caller passed non-default (e.g., topic's 10), respect it
                logger.info(f"Grammar mode - using: temp={temperature}, top_p={top_p}, top_k={top_k}")
            else:
                # Free-form mode: use model recommendations as fallback for default values
                if temperature == 0.7:  # User didn't override default
                    temperature = recommended_settings.get("temperature", 0.7)
                if top_p == 0.7:  # User didn't override default
                    top_p = recommended_settings.get("top_p", 0.7)
                if top_k == 40:  # User didn't override default
                    top_k = recommended_settings.get("top_k", 40)
                # If user provided non-default values, respect them
            
            max_tokens = max_tokens or recommended_settings.get("max_tokens", 512)
            
            # Ensure we have a server running for this model
            server = await self._ensure_server_running(
                model=model,
                temperature=temperature,
                top_p=top_p,
                top_k=top_k,
                json_mode=json_mode,
                grammar_file=grammar_file
            )

            # Pre-warm KV cache if not already done (saves ~100ms on first request)
            if not server.pre_warmed:
                await self._prewarm_cache(server, system_prompt)

            # Prepare request data
            request_data = {
                "prompt": formatted_prompt,
                "temperature": temperature,
                "top_p": top_p,
                "top_k": top_k,
                "max_tokens": max_tokens,
                "stop": [] if json_mode else ["<|im_end|>", "<|im_start|>", "<think>", "</think>"],
                "cache_prompt": True  # Enable KV cache reuse for common prompt prefix
            }
            
            # Only include grammar in request if json_mode is True AND no grammar file is specified
            # When using a grammar file, the server is already configured with it
            if json_mode and not grammar_file:
                request_data["grammar"] = self.get_grammar('json').strip()

            # Log the prompt being sent (truncated for readability)
            prompt_preview = formatted_prompt[-200:] if len(formatted_prompt) > 200 else formatted_prompt
            logger.info(f"Sending to LLM: ...{prompt_preview}")

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

                    # Log the full result for debugging
                    logger.debug(f"Server response result: {result}")

                    # Try multiple fields for response text (different llama-server versions use different field names)
                    response_text = result.get("content") or result.get("text") or result.get("completion") or ""

                    # Log if content is empty
                    if not response_text:
                        logger.warning(f"Empty content in server response. Full result keys: {result.keys()}")
                        logger.warning(f"Full result: {result}")

                    # Clean up the response
                    response_text = response_text.strip()

                    # Log the raw LLM response for debugging
                    logger.info(f"LLM raw response: {response_text[:200]}{'...' if len(response_text) > 200 else ''}")

                    if json_mode:
                        # JSON mode: validate and clean JSON response
                        try:
                            # Attempt to parse as JSON to validate structure
                            parsed_json = json.loads(response_text)
                            # If successful, use the original response (preserves formatting)
                            response_text = response_text
                        except json.JSONDecodeError as e:
                            logger.warning(f"Invalid JSON response from model: {e}")
                            # Try to extract JSON from response if wrapped in other text
                            import re
                            json_match = re.search(r'\{.*\}', response_text, re.DOTALL)
                            if json_match:
                                try:
                                    parsed_json = json.loads(json_match.group())
                                    response_text = json_match.group()
                                except json.JSONDecodeError:
                                    # Fallback: return structured error as valid JSON
                                    response_text = '{"error": "Invalid JSON generated by model", "raw_response": "' + response_text.replace('"', '\\"') + '"}'
                            else:
                                # No JSON found, return error response
                                response_text = '{"error": "No JSON found in model response", "raw_response": "' + response_text.replace('"', '\\"') + '"}'
                    else:
                        # Free-form mode: remove conversation markers and clean whitespace
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
        input_path = os.path.join(self.model_path, input_model)
        if not input_path.endswith(".gguf"):
            input_path += ".gguf"
            
        output_path = os.path.join(self.model_path, output_model)
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

    def _load_config(self) -> Dict[str, Any]:
        """Load model configuration from the configuration file."""
        config_path = Path(self.config_path)
        if not config_path.exists():
            raise FileNotFoundError(f"Model configuration file not found at {config_path}")
            
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)

    def _load_grammars(self) -> Dict[str, Dict[str, Any]]:
        """Load grammar definitions from the grammars configuration file."""
        grammar_path = Path("data/grammars.yaml")
        if not grammar_path.exists():
            raise FileNotFoundError(f"Grammar configuration file not found at {grammar_path}")
            
        with open(grammar_path, 'r') as f:
            return yaml.safe_load(f)['grammars']
            
    def get_grammar(self, grammar_name: str) -> str:
        """Get a grammar definition by name from the cached grammars."""
        if grammar_name not in self.grammars:
            raise ValueError(f"Grammar '{grammar_name}' not found in configuration")
        return self.grammars[grammar_name]['grammar']
        
    def get_grammar_info(self, grammar_name: str) -> Dict[str, Any]:
        """Get additional information about a grammar from the cached grammars."""
        if grammar_name not in self.grammars:
            raise ValueError(f"Grammar '{grammar_name}' not found in configuration")
        return self.grammars[grammar_name] 