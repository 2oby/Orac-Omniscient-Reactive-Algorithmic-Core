"""
ORAC - Omniscient Reactive Algorithmic Core

A lightweight, Jetson-optimized wrapper around llama.cpp that provides:
- Direct model loading and inference via llama.cpp
- Support for GGUF models
- Optimized for NVIDIA Jetson platforms
- Comprehensive logging and monitoring
- REST API for model management
- Command-line interface
"""

__version__ = "0.2.0"

# Package metadata
__author__ = "Toby"
__email__ = "toby@example.com"
__license__ = "MIT"

# Package requirements
__requires__ = {
    "python": ">=3.8",
    "fastapi": ">=0.68.0",
    "uvicorn": ">=0.15.0",
    "pydantic": ">=1.8.0",
    "httpx": ">=0.24.0",
    "python-dotenv": ">=0.19.0",
    "loguru": ">=0.5.3",
    "pytest": ">=7.0.0",
    "pytest-asyncio": ">=0.18.0",
    "pytest-cov": ">=3.0.0",
}

# Initialize logging first
from orac.logger import get_logger

logger = get_logger(__name__)
logger.info(f"ORAC v{__version__} initializing")

# Import core functionality
from orac.models import (
    ModelInfo, ModelListResponse, ModelLoadRequest, ModelLoadResponse,
    ModelUnloadResponse, GenerationRequest, GenerationResponse
)

# This version information is for compatibility checking
version_info = {
    "version": __version__,
    "requires_python": ">=3.8"
}

# Log startup information
logger.info(f"ORAC initialization complete")