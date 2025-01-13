"""API package for quantum optimization."""
from fastapi import APIRouter
from .v1 import router as v1_router

# Create main API router
api_router = APIRouter()

# Mount v1 router
api_router.include_router(v1_router, prefix="/v1", tags=["v1"])

__all__ = ['api_router'] 