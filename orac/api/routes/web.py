"""
orac.api.routes.web
-------------------
Web interface HTML page routes.
"""

import os
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from orac.logger import get_logger
from orac.api.dependencies import get_backend_manager

logger = get_logger(__name__)

# Set up templates
TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "templates")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

router = APIRouter()


@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Serve the main web interface."""
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "title": "ORAC - Omniscient Reactive Algorithmic Core"}
    )


@router.get("/topics", response_class=HTMLResponse)
async def topics_page(request: Request):
    """Serve the topics management interface."""
    return templates.TemplateResponse(
        "topics.html",
        {"request": request, "title": "ORAC - Topics Management"}
    )


@router.get("/topics/{topic_id}", response_class=HTMLResponse)
async def topic_config_page(request: Request, topic_id: str):
    """Serve the topic configuration interface."""
    return templates.TemplateResponse(
        "topic_config.html",
        {"request": request, "topic_id": topic_id, "title": f"Topic Config - {topic_id}"}
    )


@router.get("/backends", response_class=HTMLResponse)
async def backends_page(request: Request):
    """Serve the backends management interface."""
    return templates.TemplateResponse(
        "backends.html",
        {"request": request, "title": "ORAC - Backends Management"}
    )


@router.get("/backends/{backend_id}/entities", response_class=HTMLResponse)
async def backend_entities_page(request: Request, backend_id: str):
    """Serve the backend entities configuration interface."""
    backend_manager = get_backend_manager()
    backend = backend_manager.get_backend(backend_id)
    if not backend:
        raise HTTPException(status_code=404, detail=f"Backend {backend_id} not found")
    return templates.TemplateResponse(
        "backend_entities.html",
        {"request": request, "backend_id": backend_id, "backend_name": backend.get("name", backend_id), "title": f"Configure Entities - {backend.get('name', backend_id)}"}
    )


@router.get("/backends/{backend_id}/test-grammar", response_class=HTMLResponse)
async def backend_grammar_test_page(request: Request, backend_id: str):
    """Serve the grammar testing interface."""
    backend_manager = get_backend_manager()
    backend = backend_manager.get_backend(backend_id)
    if not backend:
        raise HTTPException(status_code=404, detail=f"Backend {backend_id} not found")
    return templates.TemplateResponse(
        "backend_grammar_test.html",
        {"request": request, "backend_id": backend_id, "backend_name": backend.get("name", backend_id), "title": f"Grammar Test - {backend.get('name', backend_id)}"}
    )


@router.get("/model-config", response_class=HTMLResponse)
async def model_config(request: Request):
    """Serve the model configuration interface."""
    return templates.TemplateResponse(
        "model_config.html",
        {"request": request, "title": "ORAC - Model Configuration"}
    )
