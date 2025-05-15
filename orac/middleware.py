"""
orac.middleware
--------------
Middleware components for ORAC.
"""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from orac.logger import get_logger
import time
import json

logger = get_logger(__name__)

class PromptLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log system prompt usage."""
    
    async def dispatch(self, request: Request, call_next):
        # Only log generate endpoint
        if request.url.path == "/api/v1/generate" and request.method == "POST":
            start_time = time.time()
            
            # Get request body
            body = await request.body()
            try:
                request_data = json.loads(body)
                logger.info(
                    "Generate request",
                    extra={
                        "model": request_data.get("model"),
                        "has_system_prompt": bool(request_data.get("system_prompt")),
                        "system_prompt_length": len(request_data.get("system_prompt", "")),
                        "user_prompt_length": len(request_data.get("prompt", "")),
                        "temperature": request_data.get("temperature"),
                        "max_tokens": request_data.get("max_tokens")
                    }
                )
            except json.JSONDecodeError:
                logger.warning("Failed to parse request body for logging")
            
            # Process request
            response = await call_next(request)
            
            # Log response if it's a generate endpoint
            if response.status_code == 200:
                try:
                    response_body = await response.body()
                    response_data = json.loads(response_body)
                    
                    # Log system prompt source if available
                    if "parameters" in response_data and "system_prompt" in response_data["parameters"]:
                        prompt_info = response_data["parameters"]["system_prompt"]
                        logger.info(
                            "Generate response",
                            extra={
                                "model": response_data.get("model"),
                                "system_prompt_source": prompt_info.get("source"),
                                "elapsed_ms": response_data.get("elapsed_ms"),
                                "total_time_ms": (time.time() - start_time) * 1000
                            }
                        )
                except (json.JSONDecodeError, KeyError):
                    logger.warning("Failed to parse response body for logging")
            
            return response
        
        # For non-generate endpoints, just pass through
        return await call_next(request) 