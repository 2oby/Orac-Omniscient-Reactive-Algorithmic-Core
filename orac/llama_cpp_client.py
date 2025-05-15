"""
orac.llama_cpp_client
--------------------
A lightweight Python wrapper around the llama.cpp command-line tools that provides:
- Direct model loading and inference
- Support for specialized models like Qwen3
- Seamless integration with ORAC's existing architecture
- Support for model quantization and fine-tuning

This client uses subprocess calls to interact with the llama.cpp binaries,
providing a simple and efficient way to run inference.
"""

import os
import json
import asyncio
import subprocess
from typing import List, Dict, Any, Optional
from pathlib import Path

from orac.logger import get_logger
from orac.models import PromptResponse

# Get logger for this module
logger = get_logger(__name__)

# Path constants
LLAMA_CPP_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "third_party/llama_cpp")
LLAMA_CLI = os.path.join(LLAMA_CPP_PATH, "bin/llama-cli")
LLAMA_SERVER = os.path.join(LLAMA_CPP_PATH, "bin/llama-server")
MODELS_PATH = "/home/toby/ORAC/models/gguf"

class LlamaCppClient:
    """Client for interacting with llama.cpp binaries."""
    
    def __init__(self, models_path: str = None):
        """
        Initialize the llama.cpp client.
        
        Args:
            models_path: Optional path to models directory. Defaults to MODELS_PATH.
        """
        self.models_path = models_path or MODELS_PATH
        logger.info(f"Initializing LlamaCppClient with models path: {self.models_path}")
        
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
        
        logger.info("LlamaCppClient initialized successfully")

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

    async def generate(
        self,
        model: str,
        prompt: str,
        stream: bool = False,
        temperature: float = 0.7,
        top_p: float = 0.7,
        top_k: int = 40,
        max_tokens: Optional[int] = None,
        verbose: bool = False
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
            
        Returns:
            PromptResponse with generated text and metadata
        """
        if not prompt.strip():
            raise ValueError("Prompt cannot be empty")

        start_time = asyncio.get_event_loop().time()
        
        try:
            model_path = os.path.join(self.models_path, model)
            if not model_path.endswith(".gguf"):
                model_path += ".gguf"
                
            if not os.path.exists(model_path):
                raise FileNotFoundError(f"Model not found: {model_path}")
            
            # Add detailed model file debugging
            model_stats = os.stat(model_path)
            logger.info(f"Model file details for {model_path}:")
            logger.info(f"  Size: {model_stats.st_size} bytes")
            logger.info(f"  Permissions: {oct(model_stats.st_mode)}")
            logger.info(f"  Owner: {model_stats.st_uid}")
            logger.info(f"  Group: {model_stats.st_gid}")
            
            # Add llama-cli binary debugging
            llama_cli_stats = os.stat(LLAMA_CLI)
            logger.info(f"llama-cli binary details:")
            logger.info(f"  Path: {LLAMA_CLI}")
            logger.info(f"  Size: {llama_cli_stats.st_size} bytes")
            logger.info(f"  Permissions: {oct(llama_cli_stats.st_mode)}")
            logger.info(f"  Owner: {llama_cli_stats.st_uid}")
            logger.info(f"  Group: {llama_cli_stats.st_gid}")
            
            cmd = [
                LLAMA_CLI,
                "-m", model_path,
                "-p", prompt,
                "--temp", str(temperature),
                "--top-p", str(top_p),
                "--top-k", str(top_k),
                "--ctx-size", "2048",
                "--n-predict", str(max_tokens or 512)
            ]
            
            # Only add verbose flag if requested
            if verbose:
                cmd.append("--verbose")
            
            logger.info(f"Running llama-cli command: {' '.join(cmd)}")
            
            # Execute the command and capture output
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                stdin=asyncio.subprocess.PIPE,  # We need stdin to send EOF
                env=self.env
            )
            
            # Send EOF to stdin to signal end of input
            process.stdin.close()
            
            stdout, stderr = await process.communicate()
            
            # Log both stdout and stderr for debugging
            stdout_str = stdout.decode('utf-8', errors='replace')
            stderr_str = stderr.decode('utf-8', errors='replace')
            logger.info(f"Raw llama-cli stdout: {stdout_str!r}")
            logger.info(f"Raw llama-cli stderr: {stderr_str!r}")
            
            if process.returncode != 0:
                logger.error(f"llama-cli error: {stderr_str}")
                raise Exception(f"llama-cli error: {stderr_str}")
            
            # Extract the response - in interactive mode, the response is between the prompt and the next prompt marker
            # or between the prompt and the end of output
            response_text = ""
            if prompt in stdout_str:
                # Get everything after the prompt
                after_prompt = stdout_str.split(prompt, 1)[1]
                # Look for the next prompt marker or end of output
                if "<|im_start|>" in after_prompt:
                    response_text = after_prompt.split("<|im_start|>", 1)[0]
                else:
                    response_text = after_prompt
            else:
                response_text = stdout_str
            
            # Clean up the response
            response_text = response_text.strip()
            response_text = response_text.replace('<|im_end|>', '')
            response_text = response_text.replace('assistant', '')
            response_text = response_text.replace('<think>', '').replace('</think>', '')
            response_text = ' '.join(response_text.split())
            
            logger.info(f"Cleaned response: {response_text!r}")
            
            if not response_text:
                logger.warning("Empty response from model")
                response_text = "No response generated"
            
            elapsed_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            
            return PromptResponse(
                response=response_text,
                elapsed_ms=elapsed_ms,
                model=model,
                prompt=prompt,
                finish_reason="stop" if max_tokens else None,
                usage=None  # llama.cpp doesn't provide token usage stats
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
        
        # Start the server process
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=self.env
        )
        
        # Wait a moment for the server to start
        await asyncio.sleep(2)
        
        if process.poll() is not None:
            # Process has already terminated
            stdout, stderr = process.communicate()
            error = stderr.decode('utf-8', errors='replace')
            raise Exception(f"Failed to start llama server: {error}")
        
        logger.info(f"Started llama.cpp server for model {model} on {host}:{port}")
        return process

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