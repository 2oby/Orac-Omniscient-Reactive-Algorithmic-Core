"""
ORAC - Omniscient Reactive Algorithmic Core
-------------------------------------------

A lightweight, Jetson-optimized wrapper around Ollama that provides:
- Efficient model loading and management
- Text generation with memory optimizations
- Comprehensive logging
- CLI tools for testing and management

Designed specifically for NVIDIA Jetson platforms, with optimizations for 
the Orin Nano's memory constraints and ARM64 architecture.
"""

__version__ = "0.2.0-mvp"
__author__ = "2oby"

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
    "requires_python": ">=3.8",
    "requires_ollama": ">=0.1.14"
}

# Log startup information
logger.info(f"ORAC initialization complete")