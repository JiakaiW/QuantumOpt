"""FastAPI backend for quantum optimization visualization."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
import logging

from .api import api_router

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(title="QuantumOpt API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*", "file://", "null"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Get the frontend directory
frontend_dir = Path(__file__).parent.parent / "frontend" / "dist"

# Mount static files if the frontend is built
if frontend_dir.exists():
    app.mount("/assets", StaticFiles(directory=str(frontend_dir / "assets")), name="assets")

    @app.get("/")
    async def serve_frontend():
        return FileResponse(str(frontend_dir / "index.html"))
else:
    @app.get("/")
    async def serve_frontend():
        return {"message": "Frontend not built. Please run 'npm run build' in the frontend directory."}

# Include API routes
app.include_router(api_router, prefix="/api")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 