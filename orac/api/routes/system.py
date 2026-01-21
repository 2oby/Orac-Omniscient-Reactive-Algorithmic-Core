"""
orac.api.routes.system
----------------------
System status and health endpoints.
"""

import os
import json
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from datetime import datetime
from pathlib import Path

from orac.logger import get_logger
from orac.config import APIConfig
from orac.api.dependencies import get_client, get_last_command_storage

logger = get_logger(__name__)

router = APIRouter(tags=["System"])

# Performance log file path
PERFORMANCE_LOG_PATH = Path(os.getenv("DATA_DIR", "/app/data")) / "performance_log.json"


class PerformanceEntry(BaseModel):
    """A single performance measurement entry."""
    timestamp: str
    command: str
    topic: str
    elapsed_ms: float
    success: bool
    config_notes: Optional[str] = None  # e.g., "15W mode, Qwen3-0.6B Q8"


class PerformanceLogRequest(BaseModel):
    """Request to log a performance entry with config notes."""
    config_notes: Optional[str] = None


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint with llama-server status."""
    try:
        client = await get_client()
        llama_health = client.get_health_status()

        # Determine overall status
        if llama_health["status"] == "unhealthy":
            overall_status = "unhealthy"
        elif llama_health["status"] == "degraded":
            overall_status = "degraded"
        elif llama_health["status"] == "no_servers":
            overall_status = "healthy"  # No servers is OK - they start on demand
        else:
            overall_status = "healthy"

        return {
            "status": overall_status,
            "timestamp": datetime.utcnow().isoformat(),
            "version": APIConfig.VERSION,
            "checks": {
                "api": "healthy",
                "llama_server": llama_health["status"],
                "llama_restart_count": llama_health["total_restart_count"],
                "llama_servers": llama_health["servers"],
            }
        }
    except Exception as e:
        logger.error(f"Error in health check: {e}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "version": APIConfig.VERSION,
            "checks": {
                "api": "healthy",
                "llama_server": "error",
                "error": str(e),
            }
        }


@router.get("/v1/status")
async def get_status() -> Dict[str, Any]:
    """Get system status."""
    try:
        client = await get_client()
        models = await client.list_models()
        return {
            "status": "ok",
            "models_available": len(models),
            "version": APIConfig.VERSION
        }
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/api/last-command")
async def get_last_command() -> Dict[str, Any]:
    """Get the last command that was processed."""
    storage = get_last_command_storage()

    # Calculate current elapsed time if still processing
    elapsed_ms = storage.get("elapsed_ms")
    if storage.get("status") == "processing" and storage.get("start_time"):
        elapsed_ms = (datetime.now() - storage.get("start_time")).total_seconds() * 1000

    return {
        "command": storage.get("command", ""),
        "topic": storage.get("topic", ""),
        "timestamp": storage.get("timestamp").isoformat() if storage.get("timestamp") else None,
        "generated_json": storage.get("generated_json"),
        "ha_request": storage.get("ha_request"),
        "ha_response": storage.get("ha_response"),
        "error": storage.get("error"),
        "success": storage.get("success", False),
        # Performance tracking
        "status": storage.get("status", "idle"),
        "start_time": storage.get("start_time").isoformat() if storage.get("start_time") else None,
        "end_time": storage.get("end_time").isoformat() if storage.get("end_time") else None,
        "elapsed_ms": elapsed_ms,
        "performance_config": storage.get("performance_config"),
        # End-to-end timing breakdown
        "timing": storage.get("timing", {})
    }


@router.post("/api/performance/log")
async def log_performance(request: PerformanceLogRequest) -> Dict[str, Any]:
    """Log the current command's performance with optional config notes."""
    storage = get_last_command_storage()

    if not storage.get("command") or storage.get("elapsed_ms") is None:
        raise HTTPException(status_code=400, detail="No completed command to log")

    # Create performance entry
    entry = {
        "timestamp": datetime.now().isoformat(),
        "command": storage.get("command", ""),
        "topic": storage.get("topic", ""),
        "elapsed_ms": storage.get("elapsed_ms"),
        "success": storage.get("success", False),
        "config_notes": request.config_notes
    }

    # Load existing log
    log_entries = []
    if PERFORMANCE_LOG_PATH.exists():
        try:
            with open(PERFORMANCE_LOG_PATH, 'r') as f:
                log_entries = json.load(f)
        except Exception as e:
            logger.warning(f"Could not load existing performance log: {e}")

    # Append new entry
    log_entries.append(entry)

    # Save log
    try:
        PERFORMANCE_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(PERFORMANCE_LOG_PATH, 'w') as f:
            json.dump(log_entries, f, indent=2)
    except Exception as e:
        logger.error(f"Failed to save performance log: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save log: {e}")

    return {"status": "logged", "entry": entry, "total_entries": len(log_entries)}


@router.get("/api/performance/log")
async def get_performance_log(limit: int = 50) -> Dict[str, Any]:
    """Get recent performance log entries."""
    log_entries = []
    if PERFORMANCE_LOG_PATH.exists():
        try:
            with open(PERFORMANCE_LOG_PATH, 'r') as f:
                log_entries = json.load(f)
        except Exception as e:
            logger.warning(f"Could not load performance log: {e}")

    # Return most recent entries
    recent = log_entries[-limit:] if len(log_entries) > limit else log_entries

    # Calculate stats
    if recent:
        times = [e.get("elapsed_ms", 0) for e in recent if e.get("elapsed_ms")]
        avg_ms = sum(times) / len(times) if times else 0
        min_ms = min(times) if times else 0
        max_ms = max(times) if times else 0
    else:
        avg_ms = min_ms = max_ms = 0

    return {
        "entries": recent,
        "total_entries": len(log_entries),
        "stats": {
            "avg_ms": round(avg_ms, 1),
            "min_ms": round(min_ms, 1),
            "max_ms": round(max_ms, 1),
            "count": len(recent)
        }
    }


@router.delete("/api/performance/log")
async def clear_performance_log() -> Dict[str, Any]:
    """Clear the performance log."""
    if PERFORMANCE_LOG_PATH.exists():
        PERFORMANCE_LOG_PATH.unlink()
    return {"status": "cleared"}
