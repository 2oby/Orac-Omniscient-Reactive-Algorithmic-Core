"""
orac.api.routes.generation
---------------------------
Text generation endpoints with topic support.
"""

from fastapi import APIRouter

from orac.logger import get_logger
from orac.models import GenerationRequest, GenerationResponse
from orac.services.generation_service import GenerationService
from orac.api.dependencies import (
    get_client,
    get_topic_manager,
    get_backend_manager,
    get_backend_grammar_generator,
    get_last_command_storage
)

logger = get_logger(__name__)

router = APIRouter(tags=["Generation"])


@router.post("/v1/generate/{topic}", response_model=GenerationResponse)
async def generate_text_with_topic(topic: str, request: GenerationRequest) -> GenerationResponse:
    """Generate text using a specific topic configuration."""
    # Create service with dependencies
    service = GenerationService(
        client=await get_client(),
        topic_manager=get_topic_manager(),
        backend_manager=get_backend_manager(),
        backend_grammar_generator=get_backend_grammar_generator(),
        last_command_storage=get_last_command_storage()
    )
    return await service.generate_text(request, topic)


@router.post("/v1/generate", response_model=GenerationResponse)
async def generate_text(request: GenerationRequest) -> GenerationResponse:
    """Generate text from a model (defaults to 'general' topic for backward compatibility)."""
    # Create service with dependencies
    service = GenerationService(
        client=await get_client(),
        topic_manager=get_topic_manager(),
        backend_manager=get_backend_manager(),
        backend_grammar_generator=get_backend_grammar_generator(),
        last_command_storage=get_last_command_storage()
    )
    return await service.generate_text(request, "general")
