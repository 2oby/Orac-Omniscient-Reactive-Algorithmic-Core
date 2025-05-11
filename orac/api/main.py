from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from orac.api.routes.generate import router as generate_router
from orac.api.routes.models import router as models_router

app = FastAPI(
    title="ORAC API",
    description="API for ORAC (Omniscient Reactive Algorithmic Core) LLM service",
    version="0.1.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers with version prefix
app.include_router(generate_router, prefix="/api/v1")
app.include_router(models_router, prefix="/api/v1")

@app.get("/health")
async def health_check():
    """Health check endpoint to verify API is running."""
    return {"status": "healthy", "service": "orac"} 