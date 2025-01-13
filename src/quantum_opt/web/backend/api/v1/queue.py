"""Queue management API endpoints."""
from typing import Dict, Any
from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator
from quantum_opt.queue import TaskQueue
from ..dependencies import get_task_queue
from .....utils.events import create_api_response
from .api_schemas import APIResponse
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

class QueueStatus(BaseModel):
    """Response model for queue status."""
    active_task_id: str | None = Field(None, description="ID of the currently active task")
    task_count: int = Field(..., description="Number of tasks in the queue")
    is_processing: bool = Field(..., description="Whether the queue is currently processing tasks")
    is_paused: bool = Field(..., description="Whether the queue is paused")

class QueueControl(BaseModel):
    """Request model for queue control."""
    action: str = Field(..., description="Action to perform (start/pause/resume/stop)")
    
    @field_validator("action")
    def action_must_be_valid(cls, v: str) -> str:
        """Validate that action is one of the allowed values."""
        allowed = {"start", "pause", "resume", "stop"}
        if v not in allowed:
            raise ValueError(f"action must be one of {allowed}")
        return v

@router.get("/status", response_model=APIResponse)
async def get_queue_status(
    task_queue: TaskQueue = Depends(get_task_queue)
) -> Dict[str, Any]:
    """Get current queue status."""
    try:
        tasks = await task_queue.list_tasks()
        status = QueueStatus(
            active_task_id=None,  # We'll need to add this to TaskQueue if needed
            task_count=len(tasks),
            is_processing=task_queue.is_processing,  # Add these properties to TaskQueue
            is_paused=task_queue.is_paused
        )
        return create_api_response(
            status="success",
            data=status.model_dump()
        )
    except Exception as e:
        logger.error(f"Error getting queue status: {e}")
        return create_api_response(
            status="error",
            error={"message": str(e)}
        )

@router.post("/control", response_model=APIResponse)
async def control_queue(
    control: QueueControl,
    task_queue: TaskQueue = Depends(get_task_queue)
) -> Dict[str, Any]:
    """Control the queue (start/pause/resume/stop)."""
    try:
        if control.action == "start":
            await task_queue.start_processing()
        elif control.action == "pause":
            await task_queue.pause_processing()  # Changed to match TaskQueue method
        elif control.action == "resume":
            await task_queue.resume_processing()  # Changed to match TaskQueue method
        elif control.action == "stop":
            await task_queue.stop_processing()  # Changed to match TaskQueue method
        
        # Get updated status after action
        tasks = await task_queue.list_tasks()
        status = QueueStatus(
            active_task_id=None,  # We'll need to add this to TaskQueue if needed
            task_count=len(tasks),
            is_processing=task_queue.is_processing,  # Add these properties to TaskQueue
            is_paused=task_queue.is_paused
        )
        return create_api_response(
            status="success",
            data=status.model_dump()
        )
    except Exception as e:
        logger.error(f"Error controlling queue: {e}")
        return create_api_response(
            status="error",
            error={"message": str(e)}
        ) 