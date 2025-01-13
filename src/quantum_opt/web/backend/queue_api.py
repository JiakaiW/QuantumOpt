"""Queue API endpoints."""
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from typing import Dict, Any, List
import uuid
import asyncio
import logging
from quantum_opt.queue import TaskQueue, OptimizationTask

logger = logging.getLogger(__name__)

# Create the router and task queue
router = APIRouter()
task_queue = TaskQueue()

# Export the task queue instance
__all__ = ['router', 'task_queue']

websocket_connections: List[WebSocket] = []

@router.post("/queue/add")
async def add_task(task_data: Dict[str, Any]):
    """Add a task to the queue from the web interface."""
    try:
        # Execute the provided code to get parameter_config and objective_function
        namespace = {}
        exec(task_data["source_code"], namespace)
        
        if "parameter_config" not in namespace or "objective_function" not in namespace:
            raise ValueError("Code must define 'parameter_config' and 'objective_function'")
        
        task = OptimizationTask(
            task_id=str(uuid.uuid4()),
            name=task_data["name"],
            parameter_config=namespace["parameter_config"],
            objective_function=namespace["objective_function"],
            optimizer_config=task_data.get("optimizer_config", {}),
            execution_config=task_data.get("execution_config", {"max_workers": 2}),
            source_code=task_data["source_code"]
        )
        
        task_id = task_queue.add_task(task)
        return {"task_id": task_id}
    except Exception as e:
        logger.error(f"Error adding task: {e}")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/queue/status")
async def get_queue_status():
    """Get status of all tasks."""
    return {
        "tasks": [
            task.to_dict()
            for task in task_queue.get_all_tasks()
        ]
    }

@router.get("/queue/task/{task_id}")
async def get_task(task_id: str):
    """Get details of a specific task."""
    task = task_queue.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task.to_dict()

@router.post("/queue/task/{task_id}/cancel")
async def cancel_task(task_id: str):
    """Cancel a specific task."""
    task = task_queue.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status == 'running':
        # TODO: Implement task cancellation
        pass
    task_queue.mark_failed(task_id, "Task cancelled by user")
    return {"status": "cancelled"}

async def broadcast_queue_update(event: Dict[str, Any]):
    """Broadcast queue updates to all connected websockets."""
    message = {
        "type": "QUEUE_UPDATE",
        "data": event
    }
    for connection in websocket_connections:
        try:
            await connection.send_json(message)
        except Exception as e:
            logger.error(f"Error sending websocket message: {e}")
            websocket_connections.remove(connection)

# Set up queue event handler
task_queue.subscribe(broadcast_queue_update)

@router.websocket("/ws/queue")
async def queue_websocket(websocket: WebSocket):
    """WebSocket endpoint for real-time queue updates."""
    await websocket.accept()
    websocket_connections.append(websocket)
    
    try:
        # Send initial queue status
        await websocket.send_json({
            "type": "QUEUE_STATUS",
            "data": await get_queue_status()
        })
        
        # Keep connection alive and handle any client messages
        while True:
            await websocket.receive_text()  # Keep connection alive
            
    except WebSocketDisconnect:
        websocket_connections.remove(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        websocket_connections.remove(websocket) 