"""Tests for WebSocket manager functionality."""
import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch
from fastapi import WebSocket, WebSocketDisconnect
from quantum_opt.queue import TaskQueue
from quantum_opt.web.backend.websocket_manager import WebSocketManager
from quantum_opt.utils.events import Event, EventType, create_api_response

@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket connection."""
    websocket = AsyncMock(spec=WebSocket)
    websocket.send_json = AsyncMock()
    websocket.receive_json = AsyncMock()
    return websocket

@pytest.fixture
def mock_task_queue():
    """Create a mock TaskQueue."""
    queue = Mock(spec=TaskQueue)
    queue.add_subscriber = Mock()
    queue.list_tasks = AsyncMock(return_value=[])
    queue._current_task = None
    queue._stopped = False
    queue._is_paused = False
    return queue

@pytest.fixture
def websocket_manager(mock_task_queue):
    """Create a WebSocketManager instance with mocked dependencies."""
    manager = WebSocketManager()
    manager.initialize_queue(mock_task_queue)
    return manager

@pytest.mark.asyncio
async def test_connect_new_client(websocket_manager, mock_websocket):
    """Test connecting a new client."""
    client_id = "test-client-1"
    
    await websocket_manager.connect(mock_websocket, client_id)
    
    assert mock_websocket in websocket_manager._connections
    assert websocket_manager._reconnect_attempts[client_id] == 0
    mock_websocket.accept.assert_called_once()
    mock_websocket.send_json.assert_called_once()
    
    # Verify initial state message
    call_args = mock_websocket.send_json.call_args[0][0]
    assert call_args["status"] == "success"
    assert call_args["data"]["type"] == "INITIAL_STATE"
    assert "tasks" in call_args["data"]
    assert "queue_status" in call_args["data"]

@pytest.mark.asyncio
async def test_disconnect_client(websocket_manager, mock_websocket):
    """Test disconnecting a client."""
    client_id = "test-client-1"
    
    # First connect
    await websocket_manager.connect(mock_websocket, client_id)
    assert mock_websocket in websocket_manager._connections
    
    # Then disconnect
    await websocket_manager.disconnect(mock_websocket, client_id)
    assert mock_websocket not in websocket_manager._connections
    assert client_id in websocket_manager._reconnect_attempts
    assert websocket_manager._reconnect_attempts[client_id] == 1

@pytest.mark.asyncio
async def test_reconnection_attempts(websocket_manager, mock_websocket):
    """Test reconnection attempt tracking."""
    client_id = "test-client-1"
    
    # Connect and disconnect multiple times
    await websocket_manager.connect(mock_websocket, client_id)
    
    for _ in range(websocket_manager._max_reconnect_attempts):
        await websocket_manager.disconnect(mock_websocket, client_id)
        
    # Should be removed after max attempts
    assert client_id not in websocket_manager._reconnect_attempts

@pytest.mark.asyncio
async def test_broadcast_message(websocket_manager):
    """Test broadcasting messages to all clients."""
    # Create multiple mock clients
    clients = [AsyncMock(spec=WebSocket) for _ in range(3)]
    client_ids = [f"test-client-{i}" for i in range(3)]
    
    # Connect all clients
    for websocket, client_id in zip(clients, client_ids):
        await websocket_manager.connect(websocket, client_id)
    
    # Broadcast a test message
    test_message = create_api_response(
        status="success",
        data={"type": "TEST_EVENT", "value": "test"}
    )
    await websocket_manager.broadcast(test_message)
    
    # Verify all clients received the message
    for websocket in clients:
        websocket.send_json.assert_called_once_with(test_message)

@pytest.mark.asyncio
async def test_handle_queue_event(websocket_manager, mock_websocket):
    """Test handling queue events."""
    client_id = "test-client-1"
    await websocket_manager.connect(mock_websocket, client_id)
    
    # Create and emit a test event
    test_event = Event(
        event_type=EventType.TASK_ADDED,
        task_id="test-task-1",
        data={"status": "pending"}
    )
    await websocket_manager._handle_queue_event(test_event)
    
    # Verify the event was broadcast
    mock_websocket.send_json.assert_called_with(
        create_api_response(
            status="success",
            data=test_event.to_dict()
        )
    )

@pytest.mark.asyncio
async def test_handle_client_message(websocket_manager, mock_websocket):
    """Test handling client messages."""
    client_id = "test-client-1"
    
    # Test RECONNECT message
    message = {
        "type": "RECONNECT",
        "client_id": client_id
    }
    
    await websocket_manager.handle_client_message(mock_websocket, message)
    assert mock_websocket in websocket_manager._connections
    
    # Test invalid message type
    invalid_message = {
        "type": "INVALID_TYPE",
        "data": {}
    }
    
    await websocket_manager.handle_client_message(mock_websocket, invalid_message)
    assert mock_websocket.send_json.call_args[0][0]["status"] == "error"

@pytest.mark.asyncio
async def test_handle_disconnection_cleanup(websocket_manager):
    """Test cleanup of disconnected clients during broadcast."""
    # Create clients, some of which will disconnect
    good_client = AsyncMock(spec=WebSocket)
    bad_client = AsyncMock(spec=WebSocket)
    bad_client.send_json.side_effect = WebSocketDisconnect()
    
    # Connect clients
    await websocket_manager.connect(good_client, "good-client")
    await websocket_manager.connect(bad_client, "bad-client")
    
    # Broadcast message
    test_message = create_api_response(
        status="success",
        data={"type": "TEST_EVENT"}
    )
    await websocket_manager.broadcast(test_message)
    
    # Verify cleanup
    assert good_client in websocket_manager._connections
    assert bad_client not in websocket_manager._connections

@pytest.mark.asyncio
async def test_exponential_backoff(websocket_manager, mock_websocket):
    """Test exponential backoff for reconnection attempts."""
    client_id = "test-client-1"
    
    # Mock asyncio.sleep to track delay times
    sleep_times = []
    
    async def mock_sleep(delay):
        sleep_times.append(delay)
    
    with patch('asyncio.sleep', mock_sleep):
        await websocket_manager.connect(mock_websocket, client_id)
        
        # Trigger multiple reconnection attempts
        for _ in range(3):
            await websocket_manager.disconnect(mock_websocket, client_id)
            
        # Verify exponential backoff
        expected_delays = [
            websocket_manager._reconnect_delay,  # 1.0
            websocket_manager._reconnect_delay * 2,  # 2.0
            websocket_manager._reconnect_delay * 4   # 4.0
        ]
        assert sleep_times == expected_delays 