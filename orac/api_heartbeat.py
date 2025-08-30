"""
Heartbeat API endpoints for receiving topic status from ORAC STT
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging

from orac.topic_manager import TopicManager

logger = logging.getLogger(__name__)

# Create router for heartbeat endpoints
router = APIRouter(prefix="/v1/topics", tags=["heartbeat"])

# Get singleton topic manager
topic_manager = TopicManager()


class TopicHeartbeat(BaseModel):
    """Individual topic heartbeat data"""
    name: str = Field(..., description="Topic/wake word identifier")
    status: str = Field(..., description="Status: active, idle")
    last_triggered: Optional[datetime] = Field(None, description="Last time wake word was triggered")
    trigger_count: int = Field(0, description="Number of times triggered")
    wake_word: Optional[str] = Field(None, description="Wake word phrase")


class HeartbeatRequest(BaseModel):
    """Heartbeat request from ORAC STT"""
    instance_id: str = Field(..., description="Instance identifier")
    source: str = Field(..., description="Source system (e.g., orac_stt)")
    topics: List[TopicHeartbeat] = Field(..., description="List of topic heartbeats")
    timestamp: Optional[datetime] = Field(None, description="Heartbeat timestamp")


class HeartbeatResponse(BaseModel):
    """Response to heartbeat request"""
    status: str = Field(..., description="Processing status")
    topics_processed: int = Field(..., description="Number of topics processed")
    topics_created: int = Field(0, description="Number of new topics auto-created")
    message: str = Field(..., description="Status message")


@router.post("/heartbeat", response_model=HeartbeatResponse)
async def receive_heartbeat(request: HeartbeatRequest):
    """
    Receive heartbeat from ORAC STT containing topic status updates.
    Auto-discovers new topics and updates status for existing ones.
    """
    try:
        topics_created = 0
        topics_processed = 0
        
        logger.info(f"Received heartbeat from {request.source}/{request.instance_id} with {len(request.topics)} topics")
        
        for topic_hb in request.topics:
            topic_id = topic_hb.name.lower().replace(' ', '_')
            
            # Get or auto-discover topic
            topic = topic_manager.get_topic(topic_id)
            if not topic:
                # Auto-discover new topic
                logger.info(f"Auto-discovering new topic: {topic_id}")
                topic = topic_manager.auto_discover_topic(topic_id)
                topics_created += 1
            
            # Update heartbeat information
            topic.last_heartbeat = datetime.now()
            topic.heartbeat_status = topic_hb.status
            
            # Update wake word info if provided
            if topic_hb.wake_word:
                topic.wake_word = topic_hb.wake_word
            
            # Update trigger info
            if topic_hb.trigger_count > 0:
                topic.trigger_count = topic_hb.trigger_count
            if topic_hb.last_triggered:
                # This could be more recent than last_used (which tracks generation)
                pass  # We track these separately
            
            topics_processed += 1
        
        # Save all updates
        topic_manager.save_topics()
        
        return HeartbeatResponse(
            status="ok",
            topics_processed=topics_processed,
            topics_created=topics_created,
            message=f"Processed {topics_processed} topics, created {topics_created} new"
        )
        
    except Exception as e:
        logger.error(f"Failed to process heartbeat: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/heartbeat/status")
async def get_heartbeat_status():
    """
    Get current heartbeat status for all topics.
    Returns topics with their live status indicators.
    """
    try:
        topics = topic_manager.list_topics()
        now = datetime.now()
        
        status_data = {
            "topics": {},
            "summary": {
                "total": len(topics),
                "active": 0,
                "idle": 0,
                "unknown": 0
            }
        }
        
        for topic_id, topic in topics.items():
            # Calculate live status based on heartbeat age
            if topic.last_heartbeat:
                age_seconds = (now - topic.last_heartbeat).total_seconds()
                if age_seconds < 35:  # Fresh heartbeat (green)
                    live_status = "active"
                    status_data["summary"]["active"] += 1
                elif age_seconds < 70:  # Recent heartbeat (orange)
                    live_status = "idle"
                    status_data["summary"]["idle"] += 1
                else:  # Stale heartbeat (red)
                    live_status = "stale"
                    status_data["summary"]["unknown"] += 1
            else:
                live_status = "unknown"
                status_data["summary"]["unknown"] += 1
            
            status_data["topics"][topic_id] = {
                "name": topic.name,
                "live_status": live_status,
                "heartbeat_status": topic.heartbeat_status,
                "last_heartbeat": topic.last_heartbeat.isoformat() if topic.last_heartbeat else None,
                "wake_word": topic.wake_word,
                "trigger_count": topic.trigger_count,
                "auto_discovered": topic.auto_discovered
            }
        
        return status_data
        
    except Exception as e:
        logger.error(f"Failed to get heartbeat status: {e}")
        raise HTTPException(status_code=500, detail=str(e))