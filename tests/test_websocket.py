"""Tests for WebSocket functionality."""
import pytest
import pytest_asyncio
import logging
import asyncio
from typing import Dict, Any, AsyncGenerator
from fastapi import FastAPI, WebSocket
from fastapi.testclient import TestClient
from quantum_opt.web.backend.api.v1.router import router
from quantum_opt.queue.manager import TaskQueue
from quantum_opt.web.backend.websocket_manager import WebSocketManager
from quantum_opt.web.backend.api.dependencies import get_task_queue, get_websocket_manager
from quantum_opt.utils.events import EventType, create_api_response

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
TEST_TIMEOUT = 10  # 10 seconds timeout for tests

@pytest_asyncio.fixture
async def task_queue() -> AsyncGenerator[TaskQueue, None]:
    """Create a fresh TaskQueue instance for each test."""
    queue = TaskQueue()
    # Don't start processing yet - let the WebSocket manager handle that
    yield queue
    await queue.stop_processing()

@pytest_asyncio.fixture
async def websocket_manager(task_queue: TaskQueue) -> AsyncGenerator[WebSocketManager, None]:
    """Create a WebSocketManager instance."""
    manager = WebSocketManager()
    manager.initialize_queue(task_queue)
    # Start processing after WebSocket manager is initialized
    await task_queue.start_processing()
    yield manager
    await task_queue.stop_processing()

@pytest_asyncio.fixture
async def test_app(task_queue: TaskQueue, websocket_manager: WebSocketManager) -> AsyncGenerator[FastAPI, None]:
    """Create a FastAPI test application."""
    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    
    # Override dependencies to use our test instances
    app.dependency_overrides[get_task_queue] = lambda: task_queue
    app.dependency_overrides[get_websocket_manager] = lambda: websocket_manager
    yield app

@pytest_asyncio.fixture
async def test_client(test_app: FastAPI) -> AsyncGenerator[TestClient, None]:
    """Create a test client."""
    client = TestClient(test_app)
    yield client

def create_test_task_config() -> Dict[str, Any]:
    """Create a test task configuration."""
    return {
        "name": "test_task",
        "parameter_config": {
            "x": {"lower_bound": -1, "upper_bound": 1},
            "y": {"lower_bound": -1, "upper_bound": 1}
        },
        "optimizer_config": {
            "optimizer_type": "CMA",
            "budget": 10,
            "num_workers": 1
        },
        "execution_config": {
            "max_retries": 3,
            "timeout": 3600.0
        },
        "objective_fn": """def objective(x, y):
            return (x - 1)**2 + (y - 1)**2"""
    }

@pytest.mark.asyncio
@pytest.mark.timeout(TEST_TIMEOUT)
async def test_websocket_connection(test_client: TestClient):
    """Test basic WebSocket connection and disconnection."""
    client_id = "test-client-1"
    with test_client.websocket_connect(f"/api/v1/ws?client_id={client_id}") as websocket:
        # Test initial connection
        data = websocket.receive_json()
        assert data["status"] == "success"
        assert data["data"]["type"] == "CONNECTED"
        assert data["data"]["client_id"] == client_id

        # Test initial state
        data = websocket.receive_json()
        assert data["status"] == "success"
        assert data["data"]["type"] == "INITIAL_STATE"
        assert "tasks" in data["data"]

@pytest.mark.asyncio
@pytest.mark.timeout(TEST_TIMEOUT)
async def test_websocket_invalid_client_id(test_client: TestClient):
    """Test WebSocket connection with invalid client ID."""
    # Test empty client ID - should still work but generate UUID
    with test_client.websocket_connect("/api/v1/ws") as websocket:
        data = websocket.receive_json()
        assert data["status"] == "success"
        assert data["data"]["type"] == "CONNECTED"
        assert "client_id" in data["data"]

@pytest.mark.asyncio
@pytest.mark.timeout(TEST_TIMEOUT)
async def test_websocket_duplicate_connection(test_client: TestClient):
    """Test handling of duplicate client connections."""
    client_id = "test-client-2"
    
    # First connection should succeed
    with test_client.websocket_connect(f"/api/v1/ws?client_id={client_id}") as ws1:
        data = ws1.receive_json()
        assert data["status"] == "success"
        assert data["data"]["type"] == "CONNECTED"
        
        # Get initial state
        data = ws1.receive_json()
        assert data["status"] == "success"
        assert data["data"]["type"] == "INITIAL_STATE"
        
        # Second connection with same client ID should work
        with test_client.websocket_connect(f"/api/v1/ws?client_id={client_id}") as ws2:
            data = ws2.receive_json()
            assert data["status"] == "success"
            assert data["data"]["type"] == "CONNECTED"
            
            # Get initial state for second connection
            data = ws2.receive_json()
            assert data["status"] == "success"
            assert data["data"]["type"] == "INITIAL_STATE"
            
            # Try to send message on first connection - should fail
            try:
                ws1.send_json({
                    "type": "REQUEST_STATE",
                    "data": {}
                })
                ws1.receive_json()
                pytest.fail("First connection should be closed")
            except:
                pass  # Expected - first connection should be closed

@pytest.mark.asyncio
@pytest.mark.timeout(TEST_TIMEOUT)
async def test_websocket_task_updates(test_client: TestClient, task_queue: TaskQueue, websocket_manager: WebSocketManager):
    """Test that WebSocket receives task updates."""
    client_id = "test-client-3"

    # Create and start a task
    config = create_test_task_config()
    response = test_client.post("/api/v1/tasks", json=config)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    task_id = data["data"]["task_id"]

    with test_client.websocket_connect(f"/api/v1/ws?client_id={client_id}") as websocket:
        # Skip connection and initial state messages
        data = websocket.receive_json()  # CONNECTED message
        assert data["status"] == "success"
        assert data["data"]["type"] == "CONNECTED"

        data = websocket.receive_json()  # INITIAL_STATE message
        assert data["status"] == "success"
        assert data["data"]["type"] == "INITIAL_STATE"

        # Start the task
        response = test_client.post(f"/api/v1/tasks/{task_id}/start")
        assert response.status_code == 200

        # Should receive task update
        data = websocket.receive_json()
        assert data["status"] == "success"
        assert data["data"]["type"] == "QUEUE_EVENT"
        assert data["data"]["task_id"] == task_id

@pytest.mark.asyncio
@pytest.mark.timeout(TEST_TIMEOUT)
async def test_websocket_request_state(test_client: TestClient):
    """Test requesting current state through WebSocket."""
    client_id = "test-client-4"
    
    with test_client.websocket_connect(f"/api/v1/ws?client_id={client_id}") as websocket:
        # Skip initial messages
        data = websocket.receive_json()  # CONNECTED message
        assert data["status"] == "success"
        assert data["data"]["type"] == "CONNECTED"
        
        data = websocket.receive_json()  # INITIAL_STATE message
        assert data["status"] == "success"
        assert data["data"]["type"] == "INITIAL_STATE"
        
        # Request current state
        websocket.send_json({
            "type": "REQUEST_STATE",
            "data": {}
        })
        
        # Should receive state update
        data = websocket.receive_json()
        assert data["status"] == "success"
        assert data["data"]["type"] == "STATE_UPDATE"
        assert "tasks" in data["data"]

@pytest.mark.asyncio
@pytest.mark.timeout(TEST_TIMEOUT)
async def test_websocket_task_control(test_client: TestClient, task_queue: TaskQueue, websocket_manager: WebSocketManager):
    """Test controlling tasks through WebSocket."""
    client_id = "test-client-5"
    
    # Create a task first
    config = create_test_task_config()
    response = test_client.post("/api/v1/tasks", json=config)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    task_id = data["data"]["task_id"]
    
    with test_client.websocket_connect(f"/api/v1/ws?client_id={client_id}") as websocket:
        # Skip initial messages
        data = websocket.receive_json()  # CONNECTED message
        assert data["status"] == "success"
        assert data["data"]["type"] == "CONNECTED"
        
        data = websocket.receive_json()  # INITIAL_STATE message
        assert data["status"] == "success"
        assert data["data"]["type"] == "INITIAL_STATE"
        
        # Try to control the task
        websocket.send_json({
            "type": "CONTROL_TASK",
            "data": {
                "task_id": task_id,
                "action": "start"
            }
        })
        
        # Should receive task update
        data = websocket.receive_json()
        assert data["status"] == "success"
        assert data["data"]["type"] == "QUEUE_EVENT"
        assert data["data"]["task_id"] == task_id

@pytest.mark.asyncio
@pytest.mark.timeout(TEST_TIMEOUT)
async def test_websocket_error_handling(test_client: TestClient):
    """Test WebSocket error handling."""
    client_id = "test-client-6"

    with test_client.websocket_connect(f"/api/v1/ws?client_id={client_id}") as websocket:
        # Skip initial messages
        data = websocket.receive_json()  # CONNECTED message
        assert data["status"] == "success"
        assert data["data"]["type"] == "CONNECTED"

        data = websocket.receive_json()  # INITIAL_STATE message
        assert data["status"] == "success"
        assert data["data"]["type"] == "INITIAL_STATE"

        # Send invalid message
        websocket.send_json({
            "type": "INVALID_TYPE",
            "data": {}
        })

        # Should receive error response
        data = websocket.receive_json()
        assert data["status"] == "error"
        assert "detail" in data["error"]
        assert data["error"]["detail"] == "Invalid message type: INVALID_TYPE" 