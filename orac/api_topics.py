"""
Topic management API endpoints for ORAC
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
from pydantic import BaseModel
import logging

from orac.topic_manager import TopicManager
from orac.topic_models.topic import Topic
from orac.backend_manager import BackendManager

logger = logging.getLogger(__name__)

# Create router for topic endpoints
router = APIRouter(prefix="/api/topics", tags=["topics"])

# Initialize topic manager (singleton)
topic_manager = TopicManager()


class TopicCreateRequest(BaseModel):
    """Request model for creating a topic"""
    name: str
    description: str = ""
    model: str
    settings: Dict[str, Any] = {}
    grammar: Dict[str, Any] = {}
    dispatcher: str = None
    enabled: bool = True


class TopicUpdateRequest(BaseModel):
    """Request model for updating a topic"""
    name: str
    description: str
    model: str
    settings: Dict[str, Any]
    grammar: Dict[str, Any]
    backend_id: str = None  # Sprint 4: Backend linkage
    dispatcher: str = None  # Optional field
    enabled: bool


class TopicResponse(BaseModel):
    """Response model for a single topic"""
    id: str
    name: str
    description: str
    enabled: bool
    model: str
    settings: Dict[str, Any]
    grammar: Dict[str, Any]
    backend_id: str = None  # Sprint 4: Backend linkage
    dispatcher: str = None
    auto_discovered: bool
    first_seen: str = None
    last_used: str = None


class TopicsListResponse(BaseModel):
    """Response model for listing topics"""
    topics: Dict[str, Dict[str, Any]]


class ModelsResponse(BaseModel):
    """Response model for available models"""
    models: List[str]


class GrammarsResponse(BaseModel):
    """Response model for available grammars"""
    grammars: List[str]


@router.get("", response_model=TopicsListResponse)
async def list_topics():
    """List all topics"""
    try:
        topics = topic_manager.list_topics()
        topics_data = {}
        
        for topic_id, topic in topics.items():
            topic_dict = topic.dict()
            # Convert datetime to string if present
            if topic_dict.get('first_seen'):
                topic_dict['first_seen'] = topic_dict['first_seen'].isoformat()
            if topic_dict.get('last_used'):
                topic_dict['last_used'] = topic_dict['last_used'].isoformat()
            topics_data[topic_id] = topic_dict
        
        return TopicsListResponse(topics=topics_data)
    except Exception as e:
        logger.error(f"Failed to list topics: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models", response_model=ModelsResponse)
async def get_available_models():
    """Get list of available models"""
    try:
        models = topic_manager.get_available_models()
        return ModelsResponse(models=models)
    except Exception as e:
        logger.error(f"Failed to get available models: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/grammars", response_model=GrammarsResponse)
async def get_available_grammars():
    """Get list of available grammar files"""
    try:
        grammars = topic_manager.get_available_grammars()
        return GrammarsResponse(grammars=grammars)
    except Exception as e:
        logger.error(f"Failed to get available grammars: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{topic_id}", response_model=TopicResponse)
async def get_topic(topic_id: str):
    """Get a specific topic by ID"""
    try:
        topic = topic_manager.get_topic(topic_id)
        if not topic:
            raise HTTPException(status_code=404, detail=f"Topic '{topic_id}' not found")
        
        topic_dict = topic.dict()
        # Convert datetime to string if present
        if topic_dict.get('first_seen'):
            topic_dict['first_seen'] = topic_dict['first_seen'].isoformat()
        if topic_dict.get('last_used'):
            topic_dict['last_used'] = topic_dict['last_used'].isoformat()
        
        return TopicResponse(id=topic_id, **topic_dict)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get topic {topic_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("", response_model=TopicResponse)
async def create_topic(topic_id: str, request: TopicCreateRequest):
    """Create a new topic"""
    try:
        # Check if topic already exists
        if topic_manager.get_topic(topic_id):
            raise HTTPException(status_code=409, detail=f"Topic '{topic_id}' already exists")
        
        # Create the topic
        topic_data = request.dict()
        topic = topic_manager.create_topic(topic_id, topic_data, auto_discovered=False)
        
        topic_dict = topic.dict()
        # Convert datetime to string if present
        if topic_dict.get('first_seen'):
            topic_dict['first_seen'] = topic_dict['first_seen'].isoformat()
        if topic_dict.get('last_used'):
            topic_dict['last_used'] = topic_dict['last_used'].isoformat()
        
        return TopicResponse(id=topic_id, **topic_dict)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create topic {topic_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{topic_id}", response_model=TopicResponse)
async def update_topic(topic_id: str, request: TopicUpdateRequest):
    """Update an existing topic"""
    try:
        # Check if topic exists
        if not topic_manager.get_topic(topic_id):
            raise HTTPException(status_code=404, detail=f"Topic '{topic_id}' not found")
        
        # Update the topic
        topic_data = request.dict()
        logger.info(f"Updating topic {topic_id} with data: {topic_data}")
        topic = topic_manager.update_topic(topic_id, topic_data)
        
        topic_dict = topic.dict()
        # Convert datetime to string if present
        if topic_dict.get('first_seen'):
            topic_dict['first_seen'] = topic_dict['first_seen'].isoformat()
        if topic_dict.get('last_used'):
            topic_dict['last_used'] = topic_dict['last_used'].isoformat()
        
        return TopicResponse(id=topic_id, **topic_dict)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update topic {topic_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{topic_id}")
async def delete_topic(topic_id: str):
    """Delete a topic"""
    try:
        if topic_id == 'general':
            raise HTTPException(status_code=400, detail="Cannot delete the default 'general' topic")

        success = topic_manager.delete_topic(topic_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Topic '{topic_id}' not found")

        return {"status": "success", "message": f"Topic '{topic_id}' deleted successfully"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete topic {topic_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Sprint 4: Topic-Backend Integration Endpoints

class BackendLinkRequest(BaseModel):
    """Request model for linking a topic to a backend"""
    backend_id: str


class BackendInfoResponse(BaseModel):
    """Response model for topic's backend information"""
    backend_id: str
    name: str
    type: str
    status: Dict[str, Any]
    statistics: Dict[str, int]
    device_types: List[str]
    locations: List[str]
    grammar_generated: bool


@router.put("/{topic_id}/backend")
async def link_topic_to_backend(topic_id: str, request: BackendLinkRequest):
    """Link a topic to a backend for dynamic grammar generation"""
    try:
        # Link the topic to the backend
        topic = topic_manager.link_to_backend(topic_id, request.backend_id)

        return {
            "status": "success",
            "message": f"Topic '{topic_id}' linked to backend '{request.backend_id}'",
            "backend_id": request.backend_id
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to link topic {topic_id} to backend: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{topic_id}/backend", response_model=BackendInfoResponse)
async def get_topic_backend(topic_id: str):
    """Get backend information for a topic"""
    try:
        backend_info = topic_manager.get_topic_backend_info(topic_id)
        if not backend_info:
            raise HTTPException(status_code=404, detail=f"Topic '{topic_id}' has no linked backend")

        return BackendInfoResponse(**backend_info)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get backend info for topic {topic_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{topic_id}/backend")
async def unlink_topic_from_backend(topic_id: str):
    """Unlink a topic from its backend"""
    try:
        topic = topic_manager.link_to_backend(topic_id, None)

        return {
            "status": "success",
            "message": f"Topic '{topic_id}' unlinked from backend"
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to unlink topic {topic_id} from backend: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/backends/available")
async def get_available_backends():
    """Get list of available backends for topic configuration"""
    try:
        backend_manager = BackendManager()
        backends = backend_manager.list_backends()

        backend_list = []
        for backend_id, backend_data in backends.items():
            # Get device statistics
            devices = backend_data.get("devices", [])
            enabled_devices = [d for d in devices if d.get("enabled")]
            mapped_devices = [d for d in enabled_devices if d.get("device_type") and d.get("location")]

            backend_list.append({
                "id": backend_id,
                "name": backend_data.get("name", backend_id),
                "type": backend_data.get("type", "unknown"),
                "connected": backend_data.get("status", {}).get("connected", False),
                "total_devices": len(devices),
                "enabled_devices": len(enabled_devices),
                "mapped_devices": len(mapped_devices)
            })

        return {"backends": backend_list}
    except Exception as e:
        logger.error(f"Failed to get available backends: {e}")
        raise HTTPException(status_code=500, detail=str(e))