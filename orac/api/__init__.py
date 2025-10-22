"""
orac.api
--------
FastAPI REST API for ORAC (refactored modular structure).

Provides endpoints for:
- System status and health
- Model management (list, load, unload)
- Text generation with topic support
- Backend management (CRUD, entities, grammar generation)
- Configuration management (favorites, model settings)
- Home Assistant integration
- Web interface

This module has been decomposed from the original monolithic api.py into:
- dependencies.py: Dependency injection
- middleware.py: CORS and other middleware
- lifecycle.py: Startup/shutdown event handlers
- routes/: Route handlers organized by domain
- services/: Business logic layer
"""

import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from orac.logger import get_logger
from orac.config import APIConfig
from orac.api.middleware import setup_middleware
from orac.api.lifecycle import on_startup, on_shutdown

# Import all route modules
from orac.api.routes import system
from orac.api.routes import models
from orac.api.routes import generation
from orac.api.routes import backends
from orac.api.routes import configuration
from orac.api.routes import homeassistant
from orac.api.routes import web

# Import existing routers
from orac.api_topics import router as topics_router
from orac.api_heartbeat import router as heartbeat_router

logger = get_logger(__name__)

# Create FastAPI app
app = FastAPI(
    title=APIConfig.TITLE,
    description=APIConfig.DESCRIPTION,
    version=APIConfig.VERSION
)

# Setup middleware
setup_middleware(app)

# Set up static files and templates for web interface
# Static files are in orac/static (one level up from orac/api)
STATIC_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates")

# Verify directories exist (but don't create them - they should already exist)
if not os.path.exists(STATIC_DIR):
    logger.warning(f"Static directory not found: {STATIC_DIR}")
if not os.path.exists(TEMPLATES_DIR):
    logger.warning(f"Templates directory not found: {TEMPLATES_DIR}")

# Mount static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Include all routers
app.include_router(system.router)
app.include_router(models.router)
app.include_router(generation.router)
app.include_router(backends.router)
app.include_router(configuration.router)
app.include_router(homeassistant.router)
app.include_router(web.router)

# Include existing external routers
app.include_router(topics_router)
app.include_router(heartbeat_router)

# Register lifecycle events
app.on_event("startup")(on_startup)
app.on_event("shutdown")(on_shutdown)

logger.info(f"ORAC API initialized - v{APIConfig.VERSION}")
