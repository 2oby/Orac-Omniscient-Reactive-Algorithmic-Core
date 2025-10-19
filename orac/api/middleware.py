"""
orac.api.middleware
-------------------
FastAPI middleware configuration.

Sets up:
- CORS (Cross-Origin Resource Sharing)
- Future: Request logging, rate limiting, etc.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def setup_middleware(app: FastAPI) -> None:
    """Configure all middleware for the FastAPI application."""

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allows all origins
        allow_credentials=True,
        allow_methods=["*"],  # Allows all methods
        allow_headers=["*"],  # Allows all headers
    )
