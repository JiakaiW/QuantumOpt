"""Run the web application servers."""
import asyncio
import os
import subprocess
import uvicorn
import webbrowser
from typing import List, Optional
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .backend.queue_api import router as queue_router, task_queue
from quantum_opt.queue import OptimizationTask

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include queue API routes
app.include_router(queue_router, prefix="/api")

async def run_frontend_dev_server(host: str = "localhost", port: int = 5173):
    """Run the Vite development server for the frontend."""
    frontend_dir = Path(__file__).parent / "frontend"
    
    # Install dependencies if needed
    if not (frontend_dir / "node_modules").exists():
        print("Installing frontend dependencies...")
        subprocess.run(["npm", "install"], cwd=frontend_dir, check=True)
    
    # Start the development server
    process = await asyncio.create_subprocess_exec(
        "npm", "run", "dev",
        "--", "--host", host, "--port", str(port),
        cwd=frontend_dir,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    # Wait for server to start
    while True:
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.get(f"http://{host}:{port}") as response:
                    if response.status == 200:
                        break
        except:
            await asyncio.sleep(0.1)
    
    return process

async def run_servers(
    tasks: Optional[List[OptimizationTask]] = None,
    host: str = "localhost",
    backend_port: int = 8000,
    frontend_port: int = 5173,
    should_open_browser: bool = True
):
    """Run the FastAPI backend and frontend development servers."""
    # Initialize task queue with provided tasks
    if tasks:
        for task in tasks:
            task_queue.add_task(task)
    
    # Start task queue processing
    asyncio.create_task(task_queue.start_processing())
    
    # Start frontend development server
    frontend_process = await run_frontend_dev_server(host, frontend_port)
    
    # Configure uvicorn server
    config = uvicorn.Config(
        app=app,
        host=host,
        port=backend_port,
        log_level="info"
    )
    server = uvicorn.Server(config)
    
    # Open browser if requested
    if should_open_browser:
        webbrowser.open(f"http://{host}:{frontend_port}")
    
    try:
        # Run the backend server
        await server.serve()
    finally:
        # Clean up
        frontend_process.terminate()
        await frontend_process.wait()

if __name__ == "__main__":
    asyncio.run(run_servers()) 