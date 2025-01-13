"""FastAPI dependencies for the web backend."""
from typing import Dict, Any, Optional
from fastapi import Depends
from quantum_opt.queue import TaskQueue
from quantum_opt.web.backend.websocket_manager import WebSocketManager

# Global instances
_task_queue: Optional[TaskQueue] = None
_websocket_manager: Optional[WebSocketManager] = None

def get_task_queue() -> TaskQueue:
    """Get the global task queue instance."""
    global _task_queue
    if _task_queue is None:
        _task_queue = TaskQueue()
    return _task_queue

def get_websocket_manager() -> WebSocketManager:
    """Get the global WebSocket manager instance."""
    global _websocket_manager
    if _websocket_manager is None:
        _websocket_manager = WebSocketManager()
    return _websocket_manager 