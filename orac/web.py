"""
orac.web
--------
Web interface for ORAC.

Provides a web-based user interface for:
- Model management
- Text generation
- Configuration management
"""

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
import os

# Create FastAPI app
app = FastAPI(
    title="ORAC Web Interface",
    description="Web interface for ORAC - Omniscient Reactive Algorithmic Core",
    version="0.2.0"
)

# Set up static files and templates
STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")
TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), "templates")

# Create directories if they don't exist
os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Set up templates
templates = Jinja2Templates(directory=TEMPLATES_DIR)

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Serve the main web interface."""
    return templates.TemplateResponse(
        "index.html",
        {"request": request, "title": "ORAC - Omniscient Reactive Algorithmic Core"}
    ) 