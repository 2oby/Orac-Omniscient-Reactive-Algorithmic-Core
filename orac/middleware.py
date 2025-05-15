"""
orac.middleware
--------------
Middleware components for ORAC.
"""

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from orac.logger import get_logger
import json
import time

logger = get_logger(__name__)

class PromptLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log system prompt usage."""
    
    async def dispatch(self, request: Request, call_next):
        # Only log generate endpoint
        if request.url.path == "/api/v1/generate" and request.method == "POST":
            start_time = time.time()
            
            # Log request
            try:
                body = await request.json()
                logger.info(
                    "Generate request",
                    extra={
                        "model": body.get("model"),
                        "has_system_prompt": bool(body.get("system_prompt")),
                        "prompt_length": len(body.get("prompt", "")),
                        "system_prompt_length": len(body.get("system_prompt", "")),
                        "generation_params": {
                            k: v for k, v in body.items()
                            if k in ["max_tokens", "temperature", "top_p", "stop"]
                        }
                    }
                )
            except Exception as e:
                logger.error(f"Failed to log request: {e}")
            
            # Process request
            response = await call_next(request)
            
            # Log response if successful
            if response.status_code == 200:
                try:
                    response_body = json.loads(response.body.decode())
                    elapsed = time.time() - start_time
                    
                    logger.info(
                        "Generate response",
                        extra={
                            "model": response_body.get("model"),
                            "prompt_source": response_body.get("prompt_state", {}).get("source"),
                            "generation_time": response_body.get("timing", {}).get("generation_time"),
                            "total_time": elapsed,
                            "response_length": len(response_body.get("text", ""))
                        }
                    )
                except Exception as e:
                    logger.error(f"Failed to log response: {e}")
            
            return response
        
        # Pass through for other endpoints
        return await call_next(request) 