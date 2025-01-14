"""Tests for API endpoints."""
import pytest
from fastapi.testclient import TestClient
from typing import Dict, Any, AsyncGenerator
import asyncio
import logging
from quantum_opt.web.backend.api.v1.router import router
from quantum_opt.queue.manager import TaskQueue
from quantum_opt.web.backend.websocket_manager import WebSocketManager
from quantum_opt.web.backend.api.dependencies import get_task_queue, get_websocket_manager
from quantum_opt.utils.events import EventType
from fastapi import FastAPI

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@pytest.fixture
async def task_queue() -> AsyncGenerator[TaskQueue, None]:
    """Create a fresh TaskQueue instance for each test."""
    queue = TaskQueue()
    await queue.start_processing()
    yield queue
    await queue.stop_processing()

@pytest.fixture
def websocket_manager(task_queue: TaskQueue) -> WebSocketManager:
    """Create a WebSocketManager instance."""
    return WebSocketManager(task_queue)

@pytest.fixture
def test_app(task_queue: TaskQueue, websocket_manager: WebSocketManager) -> FastAPI:
    """Create a test FastAPI application."""
    app = FastAPI()
    app.include_router(router)
    
    app.dependency_overrides[get_task_queue] = lambda: task_queue
    app.dependency_overrides[get_websocket_manager] = lambda: websocket_manager
    
    return app

@pytest.fixture
def test_client(test_app: FastAPI) -> TestClient:
    """Create a test client."""
    return TestClient(test_app)

def create_test_task_config() -> Dict[str, Any]:
    """Create a simple test task configuration."""
    return {
        "name": "test_task",
        "parameter_config": {
            "x": {"min": -1, "max": 1},
            "y": {"min": -1, "max": 1}
        },
        "optimizer_config": {
            "type": "nevergrad",
            "budget": 10
        },
        "execution_config": {
            "max_retries": 3
        },
        "objective_fn": """def objective(x, y):
            return (x - 1)**2 + (y - 1)**2"""
    }

@pytest.mark.asyncio
async def test_create_task(test_client: TestClient):
    """Test task creation endpoint."""
    config = create_test_task_config()
    response = test_client.post("/api/v1/tasks", json=config)
    assert response.status_code == 200
    data = response.json()
    assert "data" in data
    assert "task_id" in data["data"]
    assert data["status"] == "success"

@pytest.mark.asyncio
async def test_get_task(test_client: TestClient):
    """Test getting task details."""
    # Create a task first
    config = create_test_task_config()
    create_response = test_client.post("/api/v1/tasks", json=config)
    task_id = create_response.json()["data"]["task_id"]
    
    # Get task details
    response = test_client.get(f"/api/v1/tasks/{task_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["data"]["task_id"] == task_id

@pytest.mark.asyncio
async def test_list_tasks(test_client: TestClient):
    """Test listing all tasks."""
    # Create a few tasks
    for i in range(3):
        config = create_test_task_config()
        config["name"] = f"test_task_{i}"
        test_client.post("/api/v1/tasks", json=config)
    
    # List tasks
    response = test_client.get("/api/v1/tasks")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert len(data["data"]) >= 3

@pytest.mark.asyncio
async def test_start_task(test_client: TestClient):
    """Test starting a task."""
    # Create a task
    config = create_test_task_config()
    create_response = test_client.post("/api/v1/tasks", json=config)
    task_id = create_response.json()["data"]["task_id"]
    
    # Start task
    response = test_client.post(f"/api/v1/tasks/{task_id}/start")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"

@pytest.mark.asyncio
async def test_task_control_endpoints(test_client: TestClient):
    """Test task control endpoints (pause, resume, stop)."""
    # Create and start a task
    config = create_test_task_config()
    create_response = test_client.post("/api/v1/tasks", json=config)
    task_id = create_response.json()["data"]["task_id"]
    test_client.post(f"/api/v1/tasks/{task_id}/start")
    
    # Test pause
    pause_response = test_client.post(f"/api/v1/tasks/{task_id}/pause")
    assert pause_response.status_code == 200
    assert pause_response.json()["status"] == "success"
    
    # Test resume
    resume_response = test_client.post(f"/api/v1/tasks/{task_id}/resume")
    assert resume_response.status_code == 200
    assert resume_response.json()["status"] == "success"
    
    # Test stop
    stop_response = test_client.post(f"/api/v1/tasks/{task_id}/stop")
    assert stop_response.status_code == 200
    assert stop_response.json()["status"] == "success"

@pytest.mark.asyncio
async def test_queue_control_endpoints(test_client: TestClient):
    """Test queue control endpoints."""
    # Test pause queue
    pause_response = test_client.post("/api/v1/queue/control", json={"action": "pause"})
    assert pause_response.status_code == 200
    assert pause_response.json()["status"] == "success"
    
    # Test resume queue
    resume_response = test_client.post("/api/v1/queue/control", json={"action": "resume"})
    assert resume_response.status_code == 200
    assert resume_response.json()["status"] == "success"
    
    # Test stop queue
    stop_response = test_client.post("/api/v1/queue/control", json={"action": "stop"})
    assert stop_response.status_code == 200
    assert stop_response.json()["status"] == "success"

@pytest.mark.asyncio
async def test_error_handling(test_client: TestClient):
    """Test API error handling."""
    # Test invalid task ID
    response = test_client.get("/api/v1/tasks/invalid-id")
    assert response.status_code == 404
    
    # Test invalid task configuration
    invalid_config = {"name": "test"}  # Missing required fields
    response = test_client.post("/api/v1/tasks", json=invalid_config)
    assert response.status_code == 422
    
    # Test invalid queue control action
    response = test_client.post("/api/v1/queue/control", json={"action": "invalid"})
    assert response.status_code == 422 