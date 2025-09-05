"""
Topic management API endpoints for ORAC
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, Any, List
from pydantic import BaseModel
import logging

from orac.topic_manager import TopicManager
from orac.topic_models.topic import Topic

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
    dispatcher: str = None
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