"""FastAPI backend for quantum optimization visualization."""
from fastapi import FastAPI, WebSocket, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import asyncio
import logging
import uuid
import os
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, field_validator, ConfigDict, ValidationInfo
import json
from pathlib import Path
import time

from quantum_opt.optimizers.global_optimizer import MultiprocessingGlobalOptimizer
from quantum_opt.utils.events import OptimizationEventSystem, OptimizationEvent

# Create necessary directories
CHECKPOINT_DIR = Path("./checkpoints")
LOG_DIR = Path("./logs")
CHECKPOINT_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

app = FastAPI(title="QuantumOpt API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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

# Global state
active_optimizations: Dict[str, MultiprocessingGlobalOptimizer] = {}
websocket_connections: List[WebSocket] = []

class ParameterConfig(BaseModel):
    """Configuration for a single parameter."""
    type: str
    init: float
    lower: float
    upper: float

    @field_validator('upper')
    @classmethod
    def upper_must_be_greater_than_lower(cls, v: float, info: ValidationInfo) -> float:
        """Validate that upper bound is greater than lower bound."""
        data = info.data
        if 'lower' in data and v <= data['lower']:
            raise ValueError('upper bound must be greater than lower bound')
        return v

class OptimizerConfig(BaseModel):
    """Configuration for the optimizer."""
    optimizer: str
    budget: int
    num_workers: int = 1

    @field_validator('budget')
    @classmethod
    def budget_must_be_positive(cls, v: int) -> int:
        """Validate that budget is positive."""
        if v <= 0:
            raise ValueError('budget must be positive')
        return v

class ExecutionConfig(BaseModel):
    """Configuration for execution."""
    checkpoint_dir: str = "./checkpoints"
    log_file: str = "./logs/optimization.log"
    log_level: str = "INFO"
    precompile: bool = True

class OptimizationConfig(BaseModel):
    """Configuration for optimization."""
    parameter_config: Dict[str, ParameterConfig]
    optimizer_config: OptimizerConfig
    execution_config: ExecutionConfig

    model_config = ConfigDict(arbitrary_types_allowed=True)

def rosenbrock(params: dict) -> float:
    """Rosenbrock function for testing optimization."""
    time.sleep(0.2)  # Add delay for debugging
    x1, x2 = params['x1'], params['x2']
    return (1 - x1)**2 + 100 * (x2 - x1**2)**2

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates."""
    await websocket.accept()
    websocket_connections.append(websocket)
    print("connection open")
    try:
        while True:
            await websocket.receive_text()  # Keep connection alive
    except:
        websocket_connections.remove(websocket)
        print("connection closed")

async def broadcast_update(event_type: str, data: dict):
    """Broadcast update to all connected clients."""
    message = json.dumps({
        "type": event_type,
        "data": data
    })
    for connection in websocket_connections:
        try:
            await connection.send_text(message)
        except:
            websocket_connections.remove(connection)

@app.post("/api/optimization")
async def start_optimization(config: OptimizationConfig):
    """Start a new optimization."""
    opt_id = str(uuid.uuid4())
    
    # Create event system
    event_system = OptimizationEventSystem()
    
    # Get user config values first
    user_config = config.execution_config.model_dump()
    
    # Create execution config with defaults, overridden by user values
    execution_config = ExecutionConfig(
        checkpoint_dir=user_config.get('checkpoint_dir', str(CHECKPOINT_DIR)),
        log_file=user_config.get('log_file', str(LOG_DIR / f"optimization_{opt_id}.log")),
        log_level=user_config.get('log_level', "INFO"),
        precompile=user_config.get('precompile', True)
    )
    
    # Convert configs to dictionaries for optimizer
    execution_config_dict = execution_config.model_dump()
    optimizer_config_dict = config.optimizer_config.model_dump()
    parameter_config_dict = {k: v.model_dump() for k, v in config.parameter_config.items()}
    
    # Create optimizer
    optimizer = MultiprocessingGlobalOptimizer(
        objective_fn=rosenbrock,
        parameter_config=parameter_config_dict,
        optimizer_config=optimizer_config_dict,
        execution_config=execution_config_dict
    )
    
    # Set event system
    optimizer._event_system = event_system
    
    # Store optimizer
    active_optimizations[opt_id] = optimizer
    
    # Set up event handlers
    async def on_iteration(event: OptimizationEvent):
        """Handle iteration event."""
        await broadcast_update("ITERATION_COMPLETE", {
            "optimization_id": opt_id,
            "state": {
                "iteration": event.data.get("iteration", 0),
                "value": event.data.get("value", 0),
                "best_value": event.data.get("best_value", 0)
            }
        })
    
    event_system.subscribe(OptimizationEvent.ITERATION_COMPLETE, on_iteration)
    
    # Start optimization in background
    asyncio.create_task(run_optimization(opt_id))
    
    return {"optimization_id": opt_id}

async def run_optimization(opt_id: str):
    """Run optimization in background."""
    optimizer = active_optimizations[opt_id]
    try:
        # Run optimization
        result = await optimizer.optimize()
        
        # Only broadcast completion if optimization wasn't stopped
        if opt_id in active_optimizations:
            await broadcast_update("COMPLETE", {
                "optimization_id": opt_id,
                "result": {
                    "best_value": float(result["best_value"]),
                    "best_params": {k: float(v) for k, v in result["best_params"].items()},
                    "total_evaluations": result["total_evaluations"],
                    "optimization_time": result["optimization_time"]
                }
            })
    except Exception as e:
        print(f"Optimization error: {str(e)}")  # Add debug print
        if opt_id in active_optimizations:
            await broadcast_update("ERROR", {
                "optimization_id": opt_id,
                "error": str(e)
            })
    finally:
        # Only clean up if optimization wasn't already stopped
        if opt_id in active_optimizations:
            del active_optimizations[opt_id]

@app.post("/api/optimization/pause")
async def pause_optimization():
    """Pause all optimizations."""
    for optimizer in active_optimizations.values():
        optimizer._event_system.pause()
    return {"status": "paused"}

@app.post("/api/optimization/resume")
async def resume_optimization():
    """Resume all optimizations."""
    for optimizer in active_optimizations.values():
        optimizer._event_system.resume()
    return {"status": "resumed"}

@app.post("/api/optimization/stop")
async def stop_optimization():
    """Stop all optimizations."""
    for optimizer in active_optimizations.values():
        optimizer._event_system.stop()
    return {"status": "stopped"}

@app.post("/api/optimization/{opt_id}/stop")
async def stop_optimization(opt_id: str):
    """Stop a specific optimization task."""
    if opt_id not in active_optimizations:
        raise HTTPException(status_code=404, detail="Optimization not found")
    
    # Get the optimizer
    optimizer = active_optimizations[opt_id]
    
    # Stop the optimization
    optimizer._event_system.stop()
    
    # Clean up
    del active_optimizations[opt_id]
    
    return {"status": "stopped", "optimization_id": opt_id}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 