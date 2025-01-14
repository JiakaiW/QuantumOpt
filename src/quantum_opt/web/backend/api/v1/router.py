"""V1 API router for quantum optimization."""
import logging
import uuid
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, WebSocket, WebSocketDisconnect, Query
from .api_schemas import OptimizationConfig, TaskResponse, TaskState, APIResponse, WebSocketMessage
from ...dependencies import get_task_queue, get_websocket_manager
from .....queue import TaskQueue
from .....utils.events import create_api_response
from .queue import router as queue_router
from ....backend.websocket_manager import WebSocketManager
import asyncio

logger = logging.getLogger(__name__)
router = APIRouter()

# Include queue router
router.include_router(queue_router, prefix="/queue", tags=["queue"])

@router.get("/health")
async def health_check() -> Dict[str, str]:
    """Health check endpoint."""
    return {"status": "ok"}

@router.post("/tasks", response_model=APIResponse)
async def create_task(
    config: OptimizationConfig,
    task_queue: TaskQueue = Depends(get_task_queue)
) -> Dict[str, Any]:
    """Create a new optimization task."""
    try:
        # Log incoming request
        logger.info(f"Received task creation request: {config.model_dump_json(indent=2)}")
        
        # Generate task ID
        task_id = str(uuid.uuid4())
        
        # Create task config
        task_config = config.model_dump()
        task_config["task_id"] = task_id
        
        # Log task config
        logger.info(f"Created task config: {task_config}")
        
        try:
            # Add task to queue
            await task_queue.add_task(task_config)
            logger.info(f"Successfully added task {task_id} to queue")
        except Exception as e:
            logger.error(f"Error adding task to queue: {str(e)}", exc_info=True)
            return create_api_response(
                status="error",
                error={"message": f"Error adding task to queue: {str(e)}"}
            )
        
        # Return response
        return create_api_response(
            status="success",
            data={
                "task_id": task_id,
                "status": "pending"
            }
        )
    except ValueError as e:
        logger.error(f"Validation error creating task: {str(e)}", exc_info=True)
        return create_api_response(
            status="error",
            error={"message": str(e)}
        )
    except Exception as e:
        logger.error(f"Unexpected error creating task: {str(e)}", exc_info=True)
        return create_api_response(
            status="error",
            error={"message": str(e)}
        )

@router.post("/tasks/{task_id}/start", response_model=APIResponse)
async def start_task(
    task_id: str,
    task_queue: TaskQueue = Depends(get_task_queue)
) -> Dict[str, Any]:
    """Start a task."""
    try:
        task = await task_queue.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        
        await task_queue.start_task(task_id)
        return create_api_response(
            status="success",
            data={"task_id": task_id, "status": "running"}
        )
    except Exception as e:
        logger.error(f"Error starting task {task_id}: {e}")
        return create_api_response(
            status="error",
            error={"message": str(e)}
        )

@router.post("/tasks/{task_id}/pause", response_model=APIResponse)
async def pause_task(
    task_id: str,
    task_queue: TaskQueue = Depends(get_task_queue)
) -> Dict[str, Any]:
    """Pause a task."""
    try:
        task = await task_queue.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        
        await task_queue.pause_task(task_id)
        return create_api_response(
            status="success",
            data={"task_id": task_id, "status": "paused"}
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
    """Resume a task."""
    try:
        task = await task_queue.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        
        await task_queue.resume_task(task_id)
        return create_api_response(
            status="success",
            data={"task_id": task_id, "status": "running"}
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
        task = await task_queue.get_task(task_id)
        if not task:
            raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
        
        await task_queue.stop_task(task_id)
        return create_api_response(
            status="success",
            data={"task_id": task_id, "status": "stopped"}
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
    task_queue: TaskQueue = Depends(get_task_queue),
    websocket_manager: WebSocketManager = Depends(get_websocket_manager)
) -> None:
    """WebSocket endpoint for real-time task updates."""
    if client_id is None:
        client_id = str(uuid.uuid4())
    
    logger.info(f"WebSocket connection request from client {client_id}")
    
    try:
        # Initialize WebSocket manager with task queue if not already initialized
        if websocket_manager._task_queue is None:
            websocket_manager.initialize_queue(task_queue)
            
        # Accept connection and register with manager
        await websocket.accept()
        await websocket_manager.connect(websocket, client_id)
        
        # Send connection confirmation
        await websocket.send_json(create_api_response(
            status="success",
            data={"type": "CONNECTED", "client_id": client_id}
        ))
        
        # Send initial state
        tasks = await task_queue.list_tasks()
        initial_state = create_api_response(
            status="success",
            data={
                "type": "INITIAL_STATE",
                "tasks": tasks
            }
        )
        await websocket.send_json(initial_state)
        
        # Start task processing if this is the first connection
        if len(websocket_manager._connections) == 1:
            logger.info("First client connected, starting task queue processing")
            await task_queue.start_processing()

        # Start cleanup task
        cleanup_task = asyncio.create_task(periodic_cleanup(websocket_manager))
        
        # Main message handling loop
        while True:
            try:
                data = await websocket.receive_json()
                message = WebSocketMessage(**data)  # Validate incoming message format
                
                # Handle different message types
                if message.type == "REQUEST_STATE":
                    tasks = await task_queue.list_tasks()
                    await websocket.send_json(create_api_response(
                        status="success",
                        data={
                            "type": "STATE_UPDATE",
                            "tasks": tasks
                        }
                    ))
                else:
                    await websocket_manager.handle_client_message(websocket, data)
                    
            except WebSocketDisconnect:
                logger.info(f"Client {client_id} disconnected")
                await websocket_manager.disconnect(websocket, client_id)
                break
            except Exception as e:
                logger.error(f"Error handling WebSocket message: {e}", exc_info=True)
                error_response = create_api_response(
                    status="error",
                    error={"message": str(e), "type": "WEBSOCKET_ERROR"}
                )
                try:
                    await websocket.send_json(error_response)
                except:
                    pass
                break
    except Exception as e:
        logger.error(f"WebSocket error for client {client_id}: {e}", exc_info=True)
        try:
            await websocket.close(code=1011, reason=str(e))
        except:
            pass
    finally:
        # Ensure cleanup happens
        if websocket in websocket_manager._connections.values():
            await websocket_manager.disconnect(websocket, client_id)
            logger.info(f"Cleaned up connection for client {client_id}")

async def periodic_cleanup(websocket_manager: WebSocketManager):
    """Periodically clean up stale connections."""
    while True:
        try:
            await asyncio.sleep(30)  # Run cleanup every 30 seconds
            await websocket_manager.cleanup_stale_connections()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error(f"Error in periodic cleanup: {e}")
            await asyncio.sleep(5)  # Wait a bit before retrying 