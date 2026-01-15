"""
orac.api.dependencies
----------------------
Dependency injection providers for FastAPI endpoints.

Provides singleton instances and factories for:
- LlamaCppClient
- HomeAssistantClient
- TopicManager
- BackendManager
- BackendGrammarGenerator
"""

import os
from typing import Dict, Any
from datetime import datetime

from orac.logger import get_logger
from orac.llama_cpp_client import LlamaCppClient
from orac.homeassistant.client import HomeAssistantClient
from orac.homeassistant.config import HomeAssistantConfig
from orac.topic_manager import TopicManager
from orac.backend_manager import BackendManager
from orac.backend_grammar_generator import BackendGrammarGenerator

logger = get_logger(__name__)

# Singleton instances
_client: LlamaCppClient = None
_ha_client: HomeAssistantClient = None
_topic_manager: TopicManager = None
_backend_manager: BackendManager = None
_backend_grammar_generator: BackendGrammarGenerator = None

# Storage for last command (global state)
_last_command_storage: Dict[str, Any] = {
    "command": "",
    "topic": "",
    "timestamp": None,
    "generated_json": None,
    "ha_request": None,
    "ha_response": None,
    "error": None,
    "success": False,
    # Performance tracking fields
    "status": "idle",  # "idle" | "processing" | "complete" | "error"
    "start_time": None,  # When processing started
    "end_time": None,  # When processing completed
    "elapsed_ms": None,  # Total processing time in milliseconds
    "performance_config": None  # Notes about current config (power mode, model, etc.)
}


async def get_client() -> LlamaCppClient:
    """Get or create the llama.cpp client instance."""
    global _client
    if _client is None:
        logger.info("Initializing llama.cpp client")
        model_path = os.getenv("ORAC_MODELS_PATH", os.path.join(os.path.dirname(os.path.dirname(__file__)), "models/gguf"))
        _client = LlamaCppClient(model_path=model_path)
    return _client


async def get_ha_client() -> HomeAssistantClient:
    """Get or create the Home Assistant client instance."""
    global _ha_client
    if _ha_client is None:
        logger.info("Initializing Home Assistant client")
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "homeassistant", "config.yaml")
        config = HomeAssistantConfig.from_yaml(config_path)
        _ha_client = HomeAssistantClient(config)
        # Initialize the async context manager
        await _ha_client.__aenter__()
    return _ha_client


def get_topic_manager() -> TopicManager:
    """Get or create the TopicManager singleton instance."""
    global _topic_manager
    if _topic_manager is None:
        logger.info("Initializing TopicManager")
        _topic_manager = TopicManager()
    return _topic_manager


def get_backend_manager() -> BackendManager:
    """Get or create the BackendManager singleton instance."""
    global _backend_manager
    if _backend_manager is None:
        logger.info("Initializing BackendManager")
        _backend_manager = BackendManager()
    return _backend_manager


def get_backend_grammar_generator() -> BackendGrammarGenerator:
    """Get or create the BackendGrammarGenerator singleton instance."""
    global _backend_grammar_generator
    if _backend_grammar_generator is None:
        logger.info("Initializing BackendGrammarGenerator")
        backend_manager = get_backend_manager()
        _backend_grammar_generator = BackendGrammarGenerator(backend_manager)
    return _backend_grammar_generator


def get_last_command_storage() -> Dict[str, Any]:
    """Get the last command storage dictionary."""
    global _last_command_storage
    return _last_command_storage


def set_last_command_storage(data: Dict[str, Any]) -> None:
    """Update the last command storage dictionary."""
    global _last_command_storage
    _last_command_storage.update(data)


async def cleanup_dependencies():
    """Clean up all dependency instances on shutdown."""
    global _client, _ha_client

    if _client:
        try:
            logger.info("Cleaning up llama.cpp client")
            await _client.cleanup()
        except Exception as e:
            logger.error(f"Error cleaning up client: {e}")

    if _ha_client:
        try:
            logger.info("Cleaning up Home Assistant client")
            await _ha_client.__aexit__(None, None, None)
        except Exception as e:
            logger.error(f"Error cleaning up HA client: {e}")
