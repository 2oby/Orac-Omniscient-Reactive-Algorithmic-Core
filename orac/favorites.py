"""
orac.favorites
--------------
Manages model favorites functionality.
"""

import json
from typing import Set
from pathlib import Path
from orac.logger import get_logger

logger = get_logger(__name__)

# Store favorites in a JSON file in the app directory
FAVORITES_FILE = Path("/app/data/favorites.json")

def ensure_favorites_dir():
    """Ensure the favorites directory exists."""
    FAVORITES_FILE.parent.mkdir(parents=True, exist_ok=True)

def load_favorites() -> Set[str]:
    """Load the set of favorite model names."""
    try:
        ensure_favorites_dir()
        if FAVORITES_FILE.exists():
            with open(FAVORITES_FILE, 'r') as f:
                return set(json.load(f))
        return set()
    except Exception as e:
        logger.error(f"Error loading favorites: {e}")
        return set()

def save_favorites(favorites: Set[str]):
    """Save the set of favorite model names."""
    try:
        ensure_favorites_dir()
        with open(FAVORITES_FILE, 'w') as f:
            json.dump(list(favorites), f)
    except Exception as e:
        logger.error(f"Error saving favorites: {e}")

def add_favorite(model_name: str) -> bool:
    """Add a model to favorites."""
    favorites = load_favorites()
    if model_name not in favorites:
        favorites.add(model_name)
        save_favorites(favorites)
        return True
    return False

def remove_favorite(model_name: str) -> bool:
    """Remove a model from favorites."""
    favorites = load_favorites()
    if model_name in favorites:
        favorites.remove(model_name)
        save_favorites(favorites)
        return True
    return False

def is_favorite(model_name: str) -> bool:
    """Check if a model is favorited."""
    return model_name in load_favorites() 