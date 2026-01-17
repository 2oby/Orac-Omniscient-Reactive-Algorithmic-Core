"""
orac.api.routes.cache
---------------------
STT Response Cache admin endpoints.

Provides endpoints for:
- Viewing cache statistics
- Listing cache entries
- Clearing the cache
- Manually removing entries
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional

from orac.logger import get_logger
from orac.api.dependencies import get_stt_response_cache

logger = get_logger(__name__)

router = APIRouter(prefix="/v1/cache/stt", tags=["Cache"])


class CacheEntryResponse(BaseModel):
    """Response model for a cache entry."""
    stt_text: str
    json_output: Dict[str, Any]
    entity_id: Optional[str] = None
    success_count: int
    created_at: str
    last_used_at: str


class CacheStatsResponse(BaseModel):
    """Response model for cache statistics."""
    entries: int
    max_size: int
    total_hits: int
    persist_to_disk: bool
    cache_file: Optional[str] = None


class CacheListResponse(BaseModel):
    """Response model for listing cache entries."""
    entries: List[CacheEntryResponse]
    total: int


class CacheClearResponse(BaseModel):
    """Response model for clearing the cache."""
    status: str
    entries_removed: int


@router.get("/stats", response_model=CacheStatsResponse)
async def get_cache_stats() -> CacheStatsResponse:
    """Get STT response cache statistics."""
    cache = get_stt_response_cache()
    stats = cache.get_stats()
    return CacheStatsResponse(**stats)


@router.get("/entries", response_model=CacheListResponse)
async def list_cache_entries(limit: int = 50) -> CacheListResponse:
    """List STT response cache entries (most recently used first)."""
    cache = get_stt_response_cache()
    entries = cache.list_entries(limit=limit)
    return CacheListResponse(
        entries=[CacheEntryResponse(**e) for e in entries],
        total=len(cache._cache)
    )


@router.delete("/clear", response_model=CacheClearResponse)
async def clear_cache() -> CacheClearResponse:
    """Clear all STT response cache entries."""
    cache = get_stt_response_cache()
    count = cache.clear()
    logger.info(f"Cache cleared via API: {count} entries removed")
    return CacheClearResponse(status="cleared", entries_removed=count)


@router.delete("/entry/{stt_text:path}")
async def remove_cache_entry(stt_text: str) -> Dict[str, Any]:
    """Remove a specific cache entry by STT text."""
    cache = get_stt_response_cache()
    normalized = cache.normalize(stt_text)

    if normalized in cache._cache:
        del cache._cache[normalized]
        if cache.persist_to_disk:
            cache._save_to_disk()
        logger.info(f"Cache entry removed via API: '{normalized}'")
        return {"status": "removed", "stt_text": normalized}
    else:
        raise HTTPException(status_code=404, detail=f"Cache entry not found: '{normalized}'")


@router.post("/error-correction")
async def trigger_error_correction(timeout_seconds: int = 60) -> Dict[str, Any]:
    """Manually trigger error correction (remove last cached entry)."""
    cache = get_stt_response_cache()
    removed = cache.remove_last_entry(timeout_seconds=timeout_seconds)

    if removed:
        return {"status": "removed", "message": "Last cache entry removed"}
    else:
        return {"status": "not_removed", "message": "No recent cache entry to remove"}
