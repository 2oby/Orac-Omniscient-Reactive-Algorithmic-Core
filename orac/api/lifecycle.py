"""
orac.api.lifecycle
------------------
Application lifecycle event handlers.

Handles:
- Startup: Initialize clients, load default models
- Shutdown: Clean up resources
"""

import os
import glob

from orac.logger import get_logger
from orac.llama_cpp_client import LlamaCppClient
from orac.config import load_favorites, ModelConfig
from orac.api.dependencies import get_client, cleanup_dependencies

logger = get_logger(__name__)


def _find_backend_grammar(data_dir: str) -> str | None:
    """Find the most recently modified backend-generated grammar file.

    Backend grammars are generated from Home Assistant entity discovery
    and stored as backend_*.gbnf. Using the most recent one ensures we
    start with the grammar that matches the current HA configuration.
    """
    grammar_dir = os.path.join(data_dir, "grammars")
    pattern = os.path.join(grammar_dir, "backend_*.gbnf")
    backend_grammars = glob.glob(pattern)

    if not backend_grammars:
        return None

    # Return the most recently modified backend grammar
    return max(backend_grammars, key=os.path.getmtime)


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

                # Use DATA_DIR env var (set in container) for correct path resolution
                data_dir = os.getenv("DATA_DIR", "/app/data")

                # Priority: backend-generated grammar > static default.gbnf
                # Backend grammars are created from HA entity discovery and persist across restarts
                grammar_file = _find_backend_grammar(data_dir)

                if grammar_file:
                    logger.info(f"Starting with backend-generated grammar: {grammar_file}")
                else:
                    # Fall back to static default.gbnf
                    grammar_file = os.path.join(data_dir, "grammars", "default.gbnf")
                    if os.path.exists(grammar_file):
                        logger.info(f"No backend grammar found, using static default: {grammar_file}")
                    else:
                        grammar_file = None
                        logger.warning(f"No grammar files found, starting without grammar")

                await client._ensure_server_running(
                    model=favorites["default_model"],
                    temperature=ModelConfig.GRAMMAR_TEMPERATURE,
                    top_p=ModelConfig.GRAMMAR_TOP_P,
                    top_k=ModelConfig.GRAMMAR_TOP_K,
                    json_mode=True,
                    grammar_file=grammar_file
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
