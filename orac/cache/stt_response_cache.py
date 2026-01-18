"""
orac.cache.stt_response_cache
-----------------------------
Cache for STT text -> JSON response mappings.

Caches successful command mappings to skip LLM processing for repeated commands.
For example, "turn on the lounge light" -> {"device": "light", "action": "turn on", "location": "lounge"}

Features:
- Text normalization for cache keys (lowercase, collapse whitespace)
- LRU eviction when max size exceeded
- Disk persistence for cache survival across restarts
- Error correction ("computer error" removes last cached entry)
- Success tracking per entry
"""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from collections import OrderedDict

from orac.logger import get_logger

logger = get_logger(__name__)


class STTResponseCache:
    """Cache for STT text to JSON response mappings."""

    def __init__(
        self,
        max_size: int = 500,
        cache_file: Optional[str] = None,
        persist_to_disk: bool = True
    ):
        """
        Initialize the STT response cache.

        Args:
            max_size: Maximum number of entries (LRU eviction when exceeded)
            cache_file: Path to cache file for persistence
            persist_to_disk: Whether to persist cache to disk
        """
        self.max_size = max_size
        self.persist_to_disk = persist_to_disk

        # Default cache file path
        if cache_file is None:
            data_dir = os.getenv("DATA_DIR", "/app/data")
            self.cache_file = Path(data_dir) / "stt_cache.json"
        else:
            self.cache_file = Path(cache_file)

        # OrderedDict for LRU behavior (most recently used at end)
        self._cache: OrderedDict[str, Dict[str, Any]] = OrderedDict()

        # Track last cache entry for error correction
        self._last_cached_key: Optional[str] = None
        self._last_cache_time: Optional[datetime] = None

        # Load from disk if available
        if self.persist_to_disk:
            self._load_from_disk()

        logger.info(f"STTResponseCache initialized: max_size={max_size}, entries={len(self._cache)}")

    @staticmethod
    def normalize(text: str) -> str:
        """
        Normalize text for use as cache key.

        Converts to lowercase and collapses whitespace.
        Example: "Turn on  the LOUNGE light" -> "turn on the lounge light"
        """
        return ' '.join(text.lower().split())

    def _make_key(self, stt_text: str, topic_id: str) -> str:
        """
        Create composite cache key from topic and normalized text.

        This ensures that different topics with different backends/JSON formats
        have separate cache entries for the same STT text.

        Topic ID is normalized to lowercase for consistent matching
        (handles case where API receives "Computa" but UI uses "computa").

        Example: "computa:turn on the light" vs "other_topic:turn on the light"
        """
        normalized_text = self.normalize(stt_text)
        normalized_topic = topic_id.lower()
        return f"{normalized_topic}:{normalized_text}"

    def get(self, stt_text: str, topic_id: str) -> Optional[Dict[str, Any]]:
        """
        Look up cached response for STT text within a specific topic.

        Args:
            stt_text: The STT transcription text
            topic_id: The topic identifier (ensures cache isolation per topic)

        Returns:
            Cached entry dict if found, None otherwise
        """
        key = self._make_key(stt_text, topic_id)

        if key in self._cache:
            # Move to end (most recently used)
            self._cache.move_to_end(key)

            entry = self._cache[key]
            entry["last_used_at"] = datetime.now().isoformat()

            # Track this as the last cache operation for error correction
            # This ensures "computer error" works even for cache hits, not just new stores
            self._last_cached_key = key
            self._last_cache_time = datetime.now()

            logger.info(f"Cache HIT: '{key}' (used {entry.get('success_count', 0)} times)")
            return entry

        logger.debug(f"Cache MISS: '{key}'")
        return None

    def store(
        self,
        stt_text: str,
        topic_id: str,
        json_output: Dict[str, Any],
        entity_id: Optional[str] = None
    ) -> None:
        """
        Store a successful STT -> JSON mapping in the cache for a specific topic.

        Args:
            stt_text: The original STT transcription text
            topic_id: The topic identifier (ensures cache isolation per topic)
            json_output: The LLM-generated JSON output
            entity_id: The resolved Home Assistant entity ID (optional)
        """
        key = self._make_key(stt_text, topic_id)
        normalized_text = self.normalize(stt_text)
        normalized_topic = topic_id.lower()
        now = datetime.now().isoformat()

        if key in self._cache:
            # Update existing entry
            self._cache[key]["success_count"] += 1
            self._cache[key]["last_used_at"] = now
            self._cache.move_to_end(key)
            logger.debug(f"Cache UPDATE: '{key}' (count: {self._cache[key]['success_count']})")
        else:
            # Create new entry with normalized topic_id for display/filtering
            entry = {
                "stt_text": normalized_text,
                "topic_id": normalized_topic,
                "json_output": json_output,
                "entity_id": entity_id,
                "success_count": 1,
                "created_at": now,
                "last_used_at": now
            }
            self._cache[key] = entry
            logger.info(f"Cache STORE: '{key}'")

            # LRU eviction if over max size
            while len(self._cache) > self.max_size:
                oldest_key, _ = self._cache.popitem(last=False)
                logger.debug(f"Cache EVICT (LRU): '{oldest_key}'")

        # Track for error correction
        self._last_cached_key = key
        self._last_cache_time = datetime.now()

        # Persist to disk
        if self.persist_to_disk:
            self._save_to_disk()

    def clear_last_entry_tracking(self) -> None:
        """
        Clear the last entry tracking (used when a command is NOT cached).

        This ensures error correction only removes entries from commands that
        were actually cached. If a command fails or doesn't result in a state
        change, we clear the tracking so "computer error" won't remove a
        previously cached (correct) entry.
        """
        self._last_cached_key = None
        self._last_cache_time = None
        logger.debug("Cleared last entry tracking (command was not cached)")

    def remove_last_entry(self, timeout_seconds: int = 60) -> bool:
        """
        Remove the last cached entry (for error correction).

        Called when user says "computer error" to undo the last cache entry.

        Only removes if ALL of these conditions are met:
        1. The most recent command involved the cache (either a new store OR a cache hit)
        2. That cache operation happened within timeout_seconds
        3. The tracking hasn't been cleared (cleared when a command doesn't use cache)

        This ensures:
        - "computer error" after a cached command → removes entry ✓
        - "computer error" after a cache hit → removes entry ✓
        - "computer error" after a non-cached command → removes nothing ✓
        - "computer error" after 60+ seconds → removes nothing ✓

        Args:
            timeout_seconds: Only remove if cache was used within this many seconds

        Returns:
            True if entry was removed, False otherwise
        """
        if not self._last_cached_key or not self._last_cache_time:
            logger.info("Error correction: No recent cache entry to remove (last command was not cached)")
            return False

        # Check if within timeout
        elapsed = (datetime.now() - self._last_cache_time).total_seconds()
        if elapsed > timeout_seconds:
            logger.info(f"Error correction: Last entry too old ({elapsed:.1f}s > {timeout_seconds}s)")
            return False

        # Remove the entry
        key = self._last_cached_key
        if key in self._cache:
            del self._cache[key]
            logger.info(f"Error correction: Removed cache entry '{key}'")

            # Clear tracking
            self._last_cached_key = None
            self._last_cache_time = None

            # Persist to disk
            if self.persist_to_disk:
                self._save_to_disk()

            return True

        return False

    def clear(self) -> int:
        """
        Clear all cache entries.

        Returns:
            Number of entries cleared
        """
        count = len(self._cache)
        self._cache.clear()
        self._last_cached_key = None
        self._last_cache_time = None

        if self.persist_to_disk:
            self._save_to_disk()

        logger.info(f"Cache CLEAR: Removed {count} entries")
        return count

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_hits = sum(e.get("success_count", 0) for e in self._cache.values())
        return {
            "entries": len(self._cache),
            "max_size": self.max_size,
            "total_hits": total_hits,
            "persist_to_disk": self.persist_to_disk,
            "cache_file": str(self.cache_file) if self.persist_to_disk else None
        }

    def list_entries(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        List cache entries (most recently used first).

        Args:
            limit: Maximum number of entries to return

        Returns:
            List of cache entries
        """
        # Return in reverse order (most recently used first)
        entries = list(reversed(self._cache.values()))
        return entries[:limit]

    def _load_from_disk(self) -> None:
        """Load cache from disk file.

        Handles both old format (v1, no topic_id) and new format (v2, with topic_id).
        Old entries without topic_id are skipped to prevent cross-topic contamination.
        """
        if not self.cache_file.exists():
            logger.debug(f"No cache file found at {self.cache_file}")
            return

        try:
            with open(self.cache_file, 'r') as f:
                data = json.load(f)

            version = data.get("version", 1)
            loaded = 0
            skipped = 0

            # Reconstruct OrderedDict from list of entries
            for entry in data.get("entries", []):
                stt_text = entry.get("stt_text")
                topic_id = entry.get("topic_id")

                if not stt_text:
                    skipped += 1
                    continue

                # Skip old entries without topic_id (incompatible format)
                if not topic_id:
                    skipped += 1
                    logger.debug(f"Skipping old cache entry without topic_id: '{stt_text}'")
                    continue

                # Reconstruct composite key from topic_id and stt_text
                key = f"{topic_id}:{stt_text}"
                self._cache[key] = entry
                loaded += 1

            if skipped > 0:
                logger.info(f"Loaded {loaded} entries from {self.cache_file} (skipped {skipped} old entries without topic_id)")
            else:
                logger.info(f"Loaded {loaded} entries from {self.cache_file}")

        except Exception as e:
            logger.warning(f"Failed to load cache from disk: {e}")

    def _save_to_disk(self) -> None:
        """Save cache to disk file."""
        try:
            # Ensure directory exists
            self.cache_file.parent.mkdir(parents=True, exist_ok=True)

            # Save as list of entries (preserves order)
            # Version 2: entries now include topic_id field
            data = {
                "version": 2,
                "saved_at": datetime.now().isoformat(),
                "entries": list(self._cache.values())
            }

            with open(self.cache_file, 'w') as f:
                json.dump(data, f, indent=2)

            logger.debug(f"Saved {len(self._cache)} entries to {self.cache_file}")

        except Exception as e:
            logger.error(f"Failed to save cache to disk: {e}")
