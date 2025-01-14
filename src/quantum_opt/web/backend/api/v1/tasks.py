"""Task management API endpoints."""
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from quantum_opt.queue import TaskQueue, OptimizationTask
from ..dependencies import get_task_queue
from .api_schemas import ParameterConfig, OptimizerConfig, ExecutionConfig

router = APIRouter()

class TaskCreate(BaseModel):
    """Request model for task creation."""
    name: str = Field(..., description="Name of the optimization task")
    parameter_config: Dict[str, ParameterConfig] = Field(..., description="Parameter configurations")
    optimizer_config: OptimizerConfig = Field(..., description="Optimizer configuration")
    execution_config: ExecutionConfig = Field(default_factory=ExecutionConfig, description="Execution configuration")
    objective_fn: str = Field(
        ..., 
        description="String representation of the objective function to optimize"
    )

class TaskControl(BaseModel):
    """Request model for task control."""
    action: str = Field(..., description="Action to perform (start/pause/resume/stop)")

class TaskResponse(BaseModel):
    """Response model for task data."""
    task_id: str = Field(..., description="Unique identifier for the task")
    name: str = Field(..., description="Name of the task")
    status: str = Field(..., description="Current status of the task")
    created_at: str = Field(..., description="Timestamp when the task was created")
    source_code: Optional[str] = Field(None, description="Source code of the objective function")
    result: Optional[Dict[str, Any]] = Field(None, description="Optimization results if completed")
    error: Optional[str] = Field(None, description="Error message if failed")

@router.post("", response_model=TaskResponse)
async def create_task(
    task_data: TaskCreate,
    task_queue: TaskQueue = Depends(get_task_queue)
) -> dict:
    """Create a new optimization task."""
    try:
        task = OptimizationTask(
            name=task_data.name,
            parameter_config=task_data.parameter_config,
            optimizer_config=task_data.optimizer_config,
            execution_config=task_data.execution_config,
            source_code=task_data.source_code
        )
        await task_queue.add_task(task)
        return task.to_dict()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("", response_model=List[TaskResponse])
async def list_tasks(
    task_queue: TaskQueue = Depends(get_task_queue)
) -> List[dict]:
    """Get all tasks."""
    try:
        tasks = task_queue.get_all_tasks()
        return [task.to_dict() for task in tasks]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    task_queue: TaskQueue = Depends(get_task_queue)
) -> dict:
    """Get a specific task."""
    task = task_queue.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task.to_dict()

@router.post("/{task_id}/control", response_model=TaskResponse)
async def control_task(
    task_id: str,
    control: TaskControl,
    task_queue: TaskQueue = Depends(get_task_queue)
) -> dict:
    """Control a task (start/pause/stop)."""
    task = task_queue.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
        
    try:
        if control.action == "start":
            if task.status == "paused":
                await task.resume()
            else:
                await task.start_optimization()
        elif control.action == "pause":
            await task.pause()
        elif control.action == "stop":
            await task.stop_optimization()
        else:
            raise HTTPException(status_code=400, detail="Invalid action")
            
        return task.to_dict()
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) 