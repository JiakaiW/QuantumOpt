"""WebSocket manager for real-time optimization updates.

This module provides a centralized manager for WebSocket connections, handling
client connections, disconnections, message broadcasting, and reconnection logic.
It integrates with the task queue to provide real-time updates about optimization
progress to connected clients.

The manager implements exponential backoff for reconnection attempts and provides
a buffering mechanism for events to ensure clients don't miss updates during
brief disconnections.

Example:
    manager = WebSocketManager()
    manager.initialize_queue(task_queue)
    
    # In FastAPI endpoint
    @app.websocket("/ws")
    async def websocket_endpoint(websocket: WebSocket):
        await manager.connect(websocket)
        try:
            while True:
                data = await websocket.receive_json()
                await manager.handle_client_message(websocket, data)
        except WebSocketDisconnect:
            await manager.disconnect(websocket)
"""
import asyncio
import logging
from typing import Dict, Set, Any, Optional, List
from fastapi import WebSocket, WebSocketDisconnect

from ...queue import TaskQueue
from ...utils.events import EventEmitter, Event, EventType, create_api_response

logger = logging.getLogger(__name__)

class WebSocketManager(EventEmitter):
    """Manager for WebSocket connections and real-time updates.
    
    This class manages WebSocket connections, handles client messages,
    and broadcasts optimization updates to connected clients. It includes
    reconnection logic with exponential backoff and event buffering.
    
    Attributes:
        _connections (Set[WebSocket]): Set of active WebSocket connections
        _reconnect_attempts (Dict[str, int]): Number of reconnection attempts per client
        _reconnect_delay (float): Base delay for reconnection attempts
        _max_reconnect_attempts (int): Maximum number of reconnection attempts
        _task_queue (Optional[TaskQueue]): Reference to the task queue
        _event_buffer (List[Dict]): Buffer of recent events for reconnecting clients
    """
    
    def __init__(self) -> None:
        """Initialize the WebSocket manager."""
        super().__init__()
        self._connections: Set[WebSocket] = set()
        self._reconnect_attempts: Dict[str, int] = {}
        self._reconnect_delay = 1.0  # Base delay in seconds
        self._max_reconnect_attempts = 5
        self._task_queue: Optional[TaskQueue] = None
        self._event_buffer = []
        
    def initialize_queue(self, task_queue: TaskQueue) -> None:
        """Initialize the task queue reference and subscribe to events.
        
        Args:
            task_queue: The TaskQueue instance to monitor for events.
        """
        self._task_queue = task_queue
        task_queue.add_subscriber(self._handle_queue_event)
        
    async def connect(self, websocket: WebSocket, client_id: str) -> None:
        """Accept a new WebSocket connection.
        
        This method accepts the connection, sends the initial state,
        and sets up event handling for the client.
        
        Args:
            websocket: The WebSocket connection to accept
            client_id: Unique identifier for the client
            
        Raises:
            RuntimeError: If task queue is not initialized
        """
        if not self._task_queue:
            raise RuntimeError("Task queue not initialized")
            
        await websocket.accept()
        self._connections.add(websocket)
        self._reconnect_attempts[client_id] = 0
        
        # Send initial state
        tasks = await self._task_queue.list_tasks()
        queue_status = {
            "current_task": self._task_queue._current_task,
            "is_paused": self._task_queue._is_paused,
            "is_stopped": self._task_queue._stopped
        }
        
        await websocket.send_json(
            create_api_response(
                status="success",
                data={
                    "type": "INITIAL_STATE",
                    "tasks": [task.to_dict() for task in tasks],
                    "queue_status": queue_status
                }
            )
        )
        
    async def disconnect(self, websocket: WebSocket, client_id: str) -> None:
        """Handle client disconnection.
        
        This method removes the connection and updates reconnection tracking.
        
        Args:
            websocket: The WebSocket connection that disconnected
            client_id: Unique identifier for the client
        """
        self._connections.remove(websocket)
        
        # Update reconnection attempts
        if client_id in self._reconnect_attempts:
            self._reconnect_attempts[client_id] += 1
            if self._reconnect_attempts[client_id] >= self._max_reconnect_attempts:
                del self._reconnect_attempts[client_id]
                logger.info(f"Client {client_id} exceeded max reconnection attempts")
        
    async def broadcast(self, message: Dict[str, Any]) -> None:
        """Broadcast a message to all connected clients.
        
        This method sends the message to all connected clients and handles
        any disconnections that occur during sending.
        
        Args:
            message: The message to broadcast to all clients
        """
        disconnected = set()
        for connection in self._connections:
            try:
                await connection.send_json(message)
            except WebSocketDisconnect:
                disconnected.add(connection)
            except Exception as e:
                logger.error(f"Error broadcasting message: {e}")
                disconnected.add(connection)
                
        # Clean up disconnected clients
        for connection in disconnected:
            self._connections.remove(connection)
            
    async def _handle_queue_event(self, event: Event) -> None:
        """Handle events from the task queue.
        
        This method processes events from the task queue and broadcasts
        them to all connected clients.
        
        Args:
            event: The event to process and broadcast
        """
        # Add event to buffer
        message = create_api_response(
            status="success",
            data=event.to_dict()
        )
        self._event_buffer.append(message)
        if len(self._event_buffer) > 100:  # Keep last 100 events
            self._event_buffer.pop(0)
            
        # Broadcast to all clients
        await self.broadcast(message)
        
    async def handle_client_message(self, websocket: WebSocket, message: Dict[str, Any]) -> None:
        """Handle messages received from clients.
        
        This method processes messages from clients, including reconnection
        requests and client-specific commands.
        
        Args:
            websocket: The WebSocket connection that sent the message
            message: The message received from the client
            
        Raises:
            ValueError: If message format is invalid
        """
        try:
            message_type = message.get("type")
            if not message_type:
                raise ValueError("Message missing type field")
                
            if message_type == "RECONNECT":
                client_id = message.get("client_id")
                if not client_id:
                    raise ValueError("Reconnect message missing client_id")
                    
                if client_id in self._reconnect_attempts:
                    # Calculate backoff delay
                    delay = self._reconnect_delay * (2 ** self._reconnect_attempts[client_id])
                    await asyncio.sleep(delay)
                    
                    # Send buffered events
                    for event in self._event_buffer:
                        await websocket.send_json(event)
            else:
                # Handle other message types
                await websocket.send_json(
                    create_api_response(
                        status="error",
                        error={"message": f"Unknown message type: {message_type}"}
                    )
                )
                
        except Exception as e:
            logger.error(f"Error handling client message: {e}")
            await websocket.send_json(
                create_api_response(
                    status="error",
                    error={"message": str(e)}
                )
            ) 