"""API endpoints for managing the task queue."""
import logging
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, WebSocket, HTTPException
from quantum_opt.queue import TaskQueue, OptimizationTask
import asyncio

logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Create a single task queue instance at module level
_task_queue: Optional[TaskQueue] = None

def get_task_queue() -> TaskQueue:
    """Get the singleton task queue instance."""
    global _task_queue
    if _task_queue is None:
        logger.debug("Creating new TaskQueue instance")
        _task_queue = TaskQueue()
    return _task_queue

# Keep track of connected websockets
active_connections: List[WebSocket] = []

async def get_task_objects() -> List[OptimizationTask]:
    """Get all task objects from the queue."""
    try:
        task_queue = get_task_queue()
        task_ids = task_queue.get_all_tasks()
        logger.debug(f"Found task IDs: {task_ids}")
        tasks = [task_queue.get_task(task_id) for task_id in task_ids]
        valid_tasks = [task for task in tasks if task is not None]
        logger.debug(f"Retrieved {len(valid_tasks)} valid tasks")
        return valid_tasks
    except Exception as e:
        logger.error(f"Error getting task objects: {e}", exc_info=True)
        return []

def serialize_task(task: OptimizationTask) -> Dict[str, Any]:
    """Serialize a task to a dictionary."""
    try:
        return task.to_dict()
    except Exception as e:
        logger.error(f"Error serializing task {task.task_id}: {e}")
        return {
            "task_id": task.task_id,
            "status": "error",
            "error": str(e)
        }

async def broadcast_queue_update(event: Dict[str, Any]) -> None:
    """Broadcast an update to all connected websocket clients."""
    if not active_connections:
        logger.debug("No active connections, skipping broadcast")
        return

    try:
        if event["type"] == "task_evaluation":
            # For evaluation updates, just forward the event
            update_event = event
            logger.debug(f"Broadcasting evaluation update for task {event.get('task_id')}")
        else:
            # For other updates, include full task state
            tasks = await get_task_objects()
            update_event = {
                "type": event["type"],
                "task_id": event.get("task_id"),
                "tasks": [serialize_task(task) for task in tasks]  # Include all tasks
            }
            logger.debug(f"Broadcasting {event['type']} update with {len(tasks)} tasks")
        
        logger.debug(f"Update event payload: {update_event}")
        
        # Broadcast to all connections
        for connection in active_connections[:]:  # Copy list to avoid modification during iteration
            try:
                await connection.send_json(update_event)
                logger.debug(f"Sent update to client")
            except Exception as e:
                logger.error(f"Error sending update to websocket: {e}")
                try:
                    await connection.close()
                    active_connections.remove(connection)
                except Exception as e2:
                    logger.error(f"Error closing connection: {e2}")
    except Exception as e:
        logger.error(f"Error broadcasting update: {e}", exc_info=True)

@router.websocket("/ws/queue")
async def queue_websocket(websocket: WebSocket):
    """WebSocket endpoint for real-time queue updates."""
    await websocket.accept()
    active_connections.append(websocket)
    logger.info("New WebSocket connection established")

    try:
        # Get task queue instance
        task_queue = get_task_queue()
        logger.debug("Got task queue instance")
        
        # Get current tasks and send initial state
        tasks = await get_task_objects()
        logger.debug(f"Sending initial state with {len(tasks)} tasks")
        logger.debug(f"Task IDs in initial state: {[task.task_id for task in tasks]}")
        
        initial_state = {
            "type": "initial_state",
            "tasks": [serialize_task(task) for task in tasks]
        }
        logger.debug(f"Initial state payload: {initial_state}")
        await websocket.send_json(initial_state)
        logger.debug("Sent initial state to client")
        
        # Start task processing if this is the first connection
        if len(active_connections) == 1:
            logger.info("First client connected, starting task processing")
            asyncio.create_task(task_queue.start_processing())
        else:
            # Broadcast to all other connections that a new client joined
            # This ensures all clients have the latest state
            for conn in active_connections:
                if conn != websocket:
                    try:
                        await conn.send_json(initial_state)
                    except Exception as e:
                        logger.error(f"Error broadcasting to other client: {e}")

        # Subscribe to queue updates
        task_queue.subscribe(broadcast_queue_update)
        logger.debug("Subscribed to queue updates")

        # Keep connection alive and handle client messages
        while True:
            try:
                # Wait for client messages (heartbeat or state request)
                msg = await websocket.receive_json()
                logger.debug(f"Received message from client: {msg}")
                if msg.get("type") == "request_state":
                    # Client explicitly requested current state
                    tasks = await get_task_objects()
                    state_update = {
                        "type": "state_update",
                        "tasks": [serialize_task(task) for task in tasks]
                    }
                    logger.debug(f"Sending state update: {state_update}")
                    await websocket.send_json(state_update)
            except Exception as e:
                logger.error(f"Error handling client message: {e}")
                break

    except Exception as e:
        logger.error(f"Error in websocket connection: {e}", exc_info=True)

    finally:
        if websocket in active_connections:
            active_connections.remove(websocket)
        await websocket.close()
        logger.info("WebSocket connection closed")

@router.get("/status")
async def get_queue_status():
    """Get the current status of all tasks in the queue."""
    tasks = await get_task_objects()
    return {
        "tasks": [serialize_task(task) for task in tasks]
    }

@router.post("/task/{task_id}/cancel")
async def cancel_task(task_id: str):
    """Cancel a specific task if it exists."""
    task_queue = get_task_queue()
    task = task_queue.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    
    if task.status == "running":
        await task.stop_optimization()
        return {"status": "cancelled"}
    else:
        raise HTTPException(status_code=400, detail="Task is not running") 