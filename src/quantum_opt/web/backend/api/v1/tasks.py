"""Task management API endpoints."""
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from quantum_opt.queue import TaskQueue, OptimizationTask
from ..dependencies import get_task_queue

router = APIRouter()

class TaskCreate(BaseModel):
    """Request model for task creation."""
    name: str
    parameter_config: dict
    optimizer_config: dict
    execution_config: dict
    source_code: Optional[str] = None

class TaskControl(BaseModel):
    """Request model for task control."""
    action: str

class TaskResponse(BaseModel):
    """Response model for task data."""
    task_id: str
    name: str
    status: str
    created_at: str
    source_code: Optional[str] = None
    result: Optional[dict] = None
    error: Optional[str] = None

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