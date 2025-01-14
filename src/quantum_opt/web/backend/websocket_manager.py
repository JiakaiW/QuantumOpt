"""WebSocket manager for real-time optimization updates.

This module provides a centralized manager for WebSocket connections, handling
client connections, disconnections, message broadcasting, and reconnection logic.
It integrates with the task queue to provide real-time updates about optimization
progress to connected clients.
"""
import asyncio
import logging
from typing import Dict, Set, Any, Optional, List
from fastapi import WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from ...queue import TaskQueue
from ...utils.events import EventEmitter, Event, EventType, create_api_response

logger = logging.getLogger(__name__)

class WebSocketManager:
    """Manages WebSocket connections and message broadcasting."""
    
    def __init__(self):
        """Initialize the WebSocket manager."""
        self._connections: Dict[str, WebSocket] = {}
        self._task_queue: Optional[TaskQueue] = None
        self._event_buffer: List[Dict[str, Any]] = []
        self._buffer_size = 100  # Keep last 100 events
        
    def initialize_queue(self, task_queue: TaskQueue) -> None:
        """Initialize with a TaskQueue and set up event handlers.
        
        Args:
            task_queue: The TaskQueue instance to monitor
        """
        # Clear any existing subscribers if reinitializing
        if self._task_queue:
            self._task_queue.remove_subscriber(self._handle_queue_event)
            
        self._task_queue = task_queue
        # TaskQueue inherits from EventEmitter, so we can subscribe directly
        task_queue.add_subscriber(self._handle_queue_event)
        logger.info("WebSocket manager initialized with task queue")
        
    async def connect(self, websocket: WebSocket, client_id: str) -> None:
        """Register a new WebSocket connection.
        
        Args:
            websocket: The WebSocket connection to register
            client_id: Unique identifier for the client
        """
        # Clean up any existing connection for this client
        if client_id in self._connections:
            logger.warning(f"Client {client_id} already connected, closing old connection")
            try:
                old_websocket = self._connections[client_id]
                await old_websocket.close()
                del self._connections[client_id]
            except Exception as e:
                logger.error(f"Error closing old connection for client {client_id}: {e}")
                
        self._connections[client_id] = websocket
        logger.info(f"Client {client_id} connected. Total connections: {len(self._connections)}")
        
        # Send buffered events
        for event in self._event_buffer:
            try:
                await websocket.send_json(event)
            except Exception as e:
                logger.error(f"Error sending buffered event to client {client_id}: {e}")
                
    async def disconnect(self, websocket: WebSocket, client_id: str) -> None:
        """Remove a WebSocket connection.
        
        Args:
            websocket: The WebSocket connection to remove
            client_id: The client ID to disconnect
        """
        if client_id in self._connections:
            # Only remove if this is the current connection for this client
            if self._connections[client_id] == websocket:
                del self._connections[client_id]
                logger.info(f"Client {client_id} disconnected. Remaining connections: {len(self._connections)}")
            
        try:
            await websocket.close()
        except:
            pass
            
        # Stop task processing if no more connections
        if not self._connections and self._task_queue:
            logger.info("No more connections, pausing task queue")
            await self._task_queue.pause_processing()
            
    async def broadcast(self, event: Event) -> None:
        """Broadcast an event to all connected clients."""
        if not self._task_queue:
            logger.error("Task queue not initialized")
            return

        # Convert event to JSON-serializable format
        event_data = {
            "type": event.type.value,  # Convert EventType enum to string
            "task_id": event.task_id,
            "timestamp": event.timestamp.isoformat(),
            "data": event.data
        }

        for client_id, websocket in self._connections.items():
            try:
                await websocket.send_json(create_api_response(
                    status="success",
                    data=event_data
                ))
            except Exception as e:
                logger.error(f"Error broadcasting to client {client_id}: {str(e)}")
                # Don't remove client here, let the router handle disconnection
            
    async def _handle_queue_event(self, event: Event) -> None:
        """Handle events from the task queue."""
        if not self._task_queue:
            logger.error("Task queue not initialized")
            return

        try:
            # Convert event to JSON-serializable format
            event_data = {
                "type": event.type.value,  # Use type.value consistently
                "task_id": event.task_id,
                "timestamp": event.timestamp.isoformat(),
                "data": event.data
            }

            # Add to event buffer
            self._event_buffer.append(event_data)
            if len(self._event_buffer) > self._buffer_size:
                self._event_buffer.pop(0)  # Remove oldest event

            # Broadcast to all connected clients
            for client_id, websocket in self._connections.items():
                try:
                    await websocket.send_json(create_api_response(
                        status="success",
                        data=event_data
                    ))
                except Exception as e:
                    logger.error(f"Error broadcasting to client {client_id}: {str(e)}")
                    # Don't remove client here, let the router handle disconnection
        except Exception as e:
            logger.error(f"Error handling queue event: {str(e)}")
            # Continue processing other events

    async def handle_client_message(self, websocket: WebSocket, data: Dict[str, Any]) -> None:
        """Handle a message from a client."""
        if not self._task_queue:
            logger.error("Task queue not initialized")
            await websocket.send_json(create_api_response(
                status="error",
                error={"detail": "Task queue not initialized"}
            ))
            return

        try:
            message_type = data.get("type")
            message_data = data.get("data", {})

            if message_type == "CONTROL_TASK":
                task_id = message_data.get("task_id")
                action = message_data.get("action")

                if not task_id or not action:
                    await websocket.send_json(create_api_response(
                        status="error",
                        error={"detail": "Missing task_id or action in control message"}
                    ))
                    return

                # Handle task control action
                if action == "start":
                    await self._task_queue.start_task(task_id)
                elif action == "pause":
                    await self._task_queue.pause_task(task_id)
                elif action == "resume":
                    await self._task_queue.resume_task(task_id)
                elif action == "stop":
                    await self._task_queue.stop_task(task_id)
                else:
                    await websocket.send_json(create_api_response(
                        status="error",
                        error={"detail": f"Invalid action: {action}"}
                    ))
                    return

                # Send success response
                await websocket.send_json(create_api_response(
                    status="success",
                    data={
                        "type": "QUEUE_EVENT",
                        "event_type": "TASK_CONTROL",
                        "task_id": task_id,
                        "action": action
                    }
                ))

            elif message_type == "REQUEST_STATE":
                # Get current state of all tasks
                tasks = await self._task_queue.list_tasks()
                await websocket.send_json(create_api_response(
                    status="success",
                    data={
                        "type": "STATE_UPDATE",
                        "tasks": tasks
                    }
                ))

            else:
                await websocket.send_json(create_api_response(
                    status="error",
                    error={"detail": f"Invalid message type: {message_type}"}
                ))

        except Exception as e:
            logger.error(f"Error handling client message: {str(e)}")
            try:
                error_response = create_api_response(
                    status="error",
                    error={"detail": f"Error handling message: {str(e)}"}
                )
                await websocket.send_json(error_response)
            except Exception as e:
                logger.error(f"Error sending error response: {str(e)}")
                # Let the router handle disconnection

    async def send_buffered_events(self, websocket: WebSocket, client_id: str) -> None:
        """Send buffered events to a newly connected client."""
        if not self._task_queue:
            logger.error("Task queue not initialized")
            return

        for event in self._event_buffer:
            try:
                # Convert event to JSON-serializable format
                event_data = {
                    "type": event.type.value,  # Convert EventType enum to string
                    "task_id": event.task_id,
                    "timestamp": event.timestamp.isoformat(),
                    "data": event.data
                }
                await websocket.send_json(create_api_response(
                    status="success",
                    data=event_data
                ))
            except Exception as e:
                logger.error(f"Error sending buffered event to client {client_id}: {str(e)}")
                # Don't remove client here, let the router handle disconnection 

    async def cleanup_stale_connections(self) -> None:
        """Clean up any stale connections."""
        stale_clients = []
        for client_id, websocket in self._connections.items():
            try:
                # Try to send a ping
                await websocket.send_json({"type": "ping"})
            except Exception as e:
                logger.warning(f"Found stale connection for client {client_id}: {e}")
                stale_clients.append((client_id, websocket))
        
        # Clean up stale connections
        for client_id, websocket in stale_clients:
            await self.disconnect(websocket, client_id) 