"""
orac.client
-----------
Client for interacting with llama.cpp models.
"""

from orac.logger import get_logger
from typing import Optional, List, Dict, Any
import os
import asyncio
import threading
from pathlib import Path
import subprocess
import json
import tempfile

logger = get_logger(__name__)

class LlamaCppClient:
    """Client for interacting with llama.cpp models."""
    
    def __init__(self):
        self._models: Dict[str, Any] = {}
        self._model_dir = os.getenv('MODEL_DIR', '/app/models/gguf')
        self._model_locks: Dict[str, asyncio.Lock] = {}
        self._global_lock = threading.Lock()
        
        # Find llama.cpp binary
        llama_cpp_dir = os.getenv('LLAMA_CPP_DIR', '/app/third_party/llama_cpp')
        self._llama_cpp_path = os.path.join(llama_cpp_dir, 'bin', 'llama-cli')
        
        if not os.path.exists(self._llama_cpp_path):
            raise RuntimeError(
                f"Could not find llama.cpp binary at {self._llama_cpp_path}. "
                "Please ensure llama.cpp is built and LLAMA_CPP_DIR is set correctly."
            )
        
        if not os.access(self._llama_cpp_path, os.X_OK):
            raise RuntimeError(
                f"llama.cpp binary at {self._llama_cpp_path} is not executable. "
                "Please check permissions."
            )
        
        logger.info(f"Initialized LlamaCppClient with model directory: {self._model_dir}")
        logger.info(f"Using llama.cpp binary at: {self._llama_cpp_path}")
        
        # Verify model directory exists
        if not os.path.exists(self._model_dir):
            logger.warning(f"Model directory {self._model_dir} does not exist")
            os.makedirs(self._model_dir, exist_ok=True)
            logger.info(f"Created model directory: {self._model_dir}")

    def _get_model_lock(self, model_name: str) -> asyncio.Lock:
        """Get or create a lock for a specific model."""
        with self._global_lock:
            if model_name not in self._model_locks:
                self._model_locks[model_name] = asyncio.Lock()
            return self._model_locks[model_name]

    def _get_model_path(self, model_name: str) -> str:
        """Get the full path to a model file."""
        # Try with and without .gguf extension
        possible_paths = [
            Path(self._model_dir) / f"{model_name}.gguf",
            Path(self._model_dir) / model_name
        ]
        
        for path in possible_paths:
            if path.exists():
                return str(path)
        
        raise ValueError(
            f"Model file not found. Tried: {', '.join(str(p) for p in possible_paths)}"
        )

    async def generate(
        self,
        prompt: str,
        model: str,
        max_tokens: int = 512,
        temperature: float = 0.7,
        top_p: float = 0.9,
        stop: Optional[List[str]] = None
    ) -> str:
        """Generate text using the specified model."""
        model_lock = self._get_model_lock(model)
        async with model_lock:
            try:
                # Get model path
                model_path = self._get_model_path(model)
                
                # Create temporary file for prompt
                with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
                    f.write(prompt)
                    prompt_file = f.name
                
                try:
                    # Prepare command
                    cmd = [
                        self._llama_cpp_path,
                        '--model', model_path,
                        '--prompt-file', prompt_file,
                        '--n-predict', str(max_tokens),
                        '--temp', str(temperature),
                        '--top-p', str(top_p),
                        '--ctx-size', '4096',  # Reasonable context size
                        '--repeat-penalty', '1.1',
                        '--no-display-prompt',  # Don't include prompt in output
                        '--json'  # Output in JSON format
                    ]
                    
                    if stop:
                        cmd.extend(['--stop', ','.join(stop)])
                    
                    # Run generation
                    logger.debug(f"Running command: {' '.join(cmd)}")
                    process = await asyncio.create_subprocess_exec(
                        *cmd,
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE
                    )
                    
                    stdout, stderr = await process.communicate()
                    
                    if process.returncode != 0:
                        error_msg = stderr.decode().strip()
                        logger.error(f"llama.cpp failed: {error_msg}")
                        raise RuntimeError(f"Model generation failed: {error_msg}")
                    
                    # Parse JSON response
                    try:
                        response = json.loads(stdout.decode())
                        content = response.get('content', '').strip()
                        if not content:
                            logger.warning("Model returned empty content")
                        return content
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse llama.cpp output: {e}")
                        logger.debug(f"Raw output: {stdout.decode()}")
                        raise RuntimeError("Failed to parse model output")
                    
                finally:
                    # Clean up temporary file
                    try:
                        os.unlink(prompt_file)
                    except Exception as e:
                        logger.warning(f"Failed to delete temporary prompt file: {e}")
                
            except Exception as e:
                logger.error(f"Generation failed for model {model}: {str(e)}")
                raise

    def list_models(self) -> List[Dict[str, Any]]:
        """List available models."""
        try:
            model_dir = Path(self._model_dir)
            if not model_dir.exists():
                logger.warning(f"Model directory {self._model_dir} does not exist")
                return []
            
            models = []
            for model_file in model_dir.glob("*.gguf"):
                try:
                    models.append({
                        "name": model_file.stem,
                        "path": str(model_file),
                        "size": model_file.stat().st_size
                    })
                except Exception as e:
                    logger.warning(f"Failed to process model file {model_file}: {e}")
            
            return sorted(models, key=lambda x: x["name"])
        except Exception as e:
            logger.error(f"Failed to list models: {str(e)}")
            return []

# Global singleton instance
client = LlamaCppClient() 