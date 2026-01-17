"""
orac.api.lifecycle
------------------
Application lifecycle event handlers.

Handles:
- Startup: Initialize clients, load default models
- Shutdown: Clean up resources
"""

import os

from orac.logger import get_logger
from orac.llama_cpp_client import LlamaCppClient
from orac.config import load_favorites, ModelConfig
from orac.api.dependencies import get_client, cleanup_dependencies

logger = get_logger(__name__)


async def on_startup():
    """Initialize the API on startup."""
    try:
        # Get client instance (creates if needed)
        client = await get_client()

        # Load default model if configured
        favorites = load_favorites()
        if favorites.get("default_model"):
            try:
                logger.info(f"Loading default model: {favorites['default_model']}")

                # Start with default.gbnf grammar for Home Assistant commands (using static default, not HA-generated)
                # Use DATA_DIR env var (set in container) for correct path resolution
                data_dir = os.getenv("DATA_DIR", "/app/data")
                grammar_file = os.path.join(data_dir, "grammars", "default.gbnf")

                if os.path.exists(grammar_file):
                    logger.info(f"Starting default model with default.gbnf grammar (static, not HA-generated): {grammar_file}")
                    await client._ensure_server_running(
                        model=favorites["default_model"],
                        temperature=ModelConfig.GRAMMAR_TEMPERATURE,
                        top_p=ModelConfig.GRAMMAR_TOP_P,
                        top_k=ModelConfig.GRAMMAR_TOP_K,
                        json_mode=True,
                        grammar_file=grammar_file
                    )
                else:
                    logger.warning(f"default.gbnf not found at {grammar_file}, falling back to set_temp.gbnf")
                    fallback_grammar = os.path.join(data_dir, "grammars", "set_temp.gbnf")

                    if os.path.exists(fallback_grammar):
                        logger.info(f"Using fallback grammar: {fallback_grammar}")
                        await client._ensure_server_running(
                            model=favorites["default_model"],
                            temperature=ModelConfig.GRAMMAR_TEMPERATURE,
                            top_p=ModelConfig.GRAMMAR_TOP_P,
                            top_k=ModelConfig.GRAMMAR_TOP_K,
                            json_mode=True,
                            grammar_file=fallback_grammar
                        )
                    else:
                        logger.warning(f"Fallback grammar not found, starting with default JSON grammar")
                        await client._ensure_server_running(
                            model=favorites["default_model"],
                            temperature=ModelConfig.DEFAULT_TEMPERATURE,
                            top_p=ModelConfig.DEFAULT_TOP_P,
                            top_k=ModelConfig.DEFAULT_TOP_K,
                            json_mode=True
                        )

                logger.info("Default model loaded successfully")

            except Exception as e:
                logger.error(f"Failed to load default model: {e}")

    except Exception as e:
        logger.error(f"Error during startup: {e}")
        raise


async def on_shutdown():
    """Clean up resources on shutdown."""
    await cleanup_dependencies()
