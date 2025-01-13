"""API dependencies for dependency injection."""
from typing import Optional
from fastapi import Depends
from quantum_opt.queue import TaskQueue
from ..websocket_manager import WebSocketManager

# Global instances
_task_queue: Optional[TaskQueue] = None
_websocket_manager: Optional[WebSocketManager] = None

def get_task_queue() -> TaskQueue:
    """Get or create TaskQueue singleton."""
    global _task_queue
    if _task_queue is None:
        _task_queue = TaskQueue()
    return _task_queue

def get_websocket_manager(
    task_queue: TaskQueue = Depends(get_task_queue)
) -> WebSocketManager:
    """Get or create WebSocketManager singleton."""
    global _websocket_manager
    if _websocket_manager is None:
        _websocket_manager = WebSocketManager()
        _websocket_manager.initialize_queue(task_queue)
    return _websocket_manager 