"""V1 API router for quantum optimization."""
import logging
import uuid
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, WebSocket, WebSocketDisconnect, Query
from .api_schemas import OptimizationConfig, TaskResponse, TaskState, APIResponse, WebSocketMessage
from ...dependencies import get_task_queue, get_websocket_manager
from .....queue import TaskQueue
from .....utils.events import create_api_response

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/tasks", response_model=APIResponse)
async def create_task(
    config: OptimizationConfig,
    task_queue: TaskQueue = Depends(get_task_queue)
) -> Dict[str, Any]:
    """Create a new optimization task."""
    try:
        task_id = str(uuid.uuid4())
        task_config = config.model_dump()
        task_config["task_id"] = task_id
        await task_queue.add_task(task_config)
        
        return create_api_response(
            status="success",
            data={"task_id": task_id, "status": "pending"}
        )
    except Exception as e:
        logger.error(f"Error creating task: {e}")
        return create_api_response(
            status="error",
            error={"message": str(e)}
        )

@router.post("/tasks/{task_id}/pause", response_model=APIResponse)
async def pause_task(
    task_id: str, 
    task_queue: TaskQueue = Depends(get_task_queue)
) -> Dict[str, Any]:
    """Pause a running task."""
    try:
        success = await task_queue.pause_task(task_id)
        if not success:
            task = await task_queue.get_task(task_id)
            if not task:
                return create_api_response(
                    status="error",
                    error={"message": f"Task {task_id} not found"}
                )
            return create_api_response(
                status="error",
                error={"message": f"Cannot pause task {task_id}: current status is {task['status']}"}
            )
        
        task = await task_queue.get_task(task_id)
        if not task:
            return create_api_response(
                status="error",
                error={"message": f"Task {task_id} not found after pausing"}
            )
            
        return create_api_response(
            status="success",
            data=TaskState(**task).model_dump()
        )
    except Exception as e:
        logger.error(f"Error pausing task {task_id}: {e}")
        return create_api_response(
            status="error",
            error={"message": str(e)}
        )

@router.post("/tasks/{task_id}/resume", response_model=APIResponse)
async def resume_task(
    task_id: str, 
    task_queue: TaskQueue = Depends(get_task_queue)
) -> Dict[str, Any]:
    """Resume a paused task."""
    try:
        success = await task_queue.resume_task(task_id)
        if not success:
            task = await task_queue.get_task(task_id)
            if not task:
                return create_api_response(
                    status="error",
                    error={"message": f"Task {task_id} not found"}
                )
            return create_api_response(
                status="error",
                error={"message": f"Cannot resume task {task_id}: current status is {task['status']}"}
            )
        
        task = await task_queue.get_task(task_id)
        if not task:
            return create_api_response(
                status="error",
                error={"message": f"Task {task_id} not found after resuming"}
            )
            
        return create_api_response(
            status="success",
            data=TaskState(**task).model_dump()
        )
    except Exception as e:
        logger.error(f"Error resuming task {task_id}: {e}")
        return create_api_response(
            status="error",
            error={"message": str(e)}
        )

@router.post("/tasks/{task_id}/stop", response_model=APIResponse)
async def stop_task(
    task_id: str, 
    task_queue: TaskQueue = Depends(get_task_queue)
) -> Dict[str, Any]:
    """Stop a task."""
    try:
        success = await task_queue.stop_task(task_id)
        if not success:
            return create_api_response(
                status="error",
                error={"message": f"Task {task_id} not found"}
            )
        
        task = await task_queue.get_task(task_id)
        if not task:
            return create_api_response(
                status="error",
                error={"message": f"Task {task_id} not found after stopping"}
            )
            
        return create_api_response(
            status="success",
            data=TaskState(**task).model_dump()
        )
    except Exception as e:
        logger.error(f"Error stopping task {task_id}: {e}")
        return create_api_response(
            status="error",
            error={"message": str(e)}
        )

@router.get("/tasks/{task_id}", response_model=APIResponse)
async def get_task(
    task_id: str, 
    task_queue: TaskQueue = Depends(get_task_queue)
) -> Dict[str, Any]:
    """Get task state."""
    try:
        task = await task_queue.get_task(task_id)
        if not task:
            return create_api_response(
                status="error",
                error={"message": f"Task {task_id} not found"}
            )
        
        return create_api_response(
            status="success",
            data=TaskState(**task).model_dump()
        )
    except Exception as e:
        logger.error(f"Error getting task {task_id}: {e}")
        return create_api_response(
            status="error",
            error={"message": str(e)}
        )

@router.get("/tasks", response_model=APIResponse)
async def list_tasks(
    task_queue: TaskQueue = Depends(get_task_queue)
) -> Dict[str, Any]:
    """List all tasks."""
    try:
        tasks = await task_queue.list_tasks()
        return create_api_response(
            status="success",
            data={"tasks": [TaskState(**task).model_dump() for task in tasks]}
        )
    except Exception as e:
        logger.error(f"Error listing tasks: {e}")
        return create_api_response(
            status="error",
            error={"message": str(e)}
        )

@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    client_id: Optional[str] = Query(None),
    websocket_manager = Depends(get_websocket_manager)
):
    """WebSocket endpoint for real-time task updates."""
    # Generate client ID if not provided
    if not client_id:
        client_id = str(uuid.uuid4())
    
    try:
        # Accept connection and send client ID
        await websocket_manager.connect(websocket, client_id)
        await websocket.send_json(
            create_api_response(
                status="success",
                data={
                    "type": "CONNECTED",
                    "client_id": client_id
                }
            )
        )
        
        # Handle messages
        while True:
            try:
                data = await websocket.receive_json()
                # Validate message format
                message = WebSocketMessage(**data)
                await websocket_manager.handle_client_message(websocket, message.model_dump())
            except WebSocketDisconnect:
                logger.info(f"Client {client_id} disconnected")
                break
            except Exception as e:
                logger.error(f"Error handling WebSocket message from client {client_id}: {e}")
                await websocket.send_json(
                    create_api_response(
                        status="error",
                        error={"message": str(e)}
                    )
                )
    except Exception as e:
        logger.error(f"WebSocket error for client {client_id}: {e}")
    finally:
        # Handle disconnection with client ID
        await websocket_manager.disconnect(websocket, client_id) 