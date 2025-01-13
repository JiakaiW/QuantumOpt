"""WebSocket API endpoints."""
from fastapi import APIRouter, WebSocket, Depends
from quantum_opt.queue import TaskQueue
from ..dependencies import get_task_queue, get_websocket_manager
from ...websocket_manager import WebSocketManager

router = APIRouter()

@router.websocket("/queue")
async def queue_websocket(
    websocket: WebSocket,
    task_queue: TaskQueue = Depends(get_task_queue),
    ws_manager: WebSocketManager = Depends(get_websocket_manager)
):
    """WebSocket endpoint for real-time queue updates."""
    try:
        # Initialize connection
        await ws_manager.connect(websocket)
        
        # Start task processing if this is the first connection
        if len(ws_manager._connections) == 1:
            await task_queue.start_processing()
            
        # Keep connection alive and handle client messages
        while True:
            try:
                message = await websocket.receive_json()
                await ws_manager.handle_client_message(websocket, message)
            except Exception as e:
                # Handle connection errors
                await ws_manager.disconnect(websocket)
                break
                
    except Exception as e:
        # Handle initialization errors
        if websocket in ws_manager._connections:
            await ws_manager.disconnect(websocket) 