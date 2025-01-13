"""Tests for web backend API endpoints."""
import pytest
from fastapi import FastAPI, WebSocketDisconnect
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch
from quantum_opt.web.backend.api.v1.router import router
from quantum_opt.web.backend.dependencies import get_task_queue, get_websocket_manager
from quantum_opt.queue import TaskQueue
from quantum_opt.web.backend.websocket_manager import WebSocketManager
from quantum_opt.optimizers.optimization_schemas import OptimizationConfig, ParameterConfig, OptimizerConfig

# Test data
@pytest.fixture
def test_config():
    """Create a test optimization configuration."""
    return {
        "name": "test_task",
        "parameter_config": {
            "x": {
                "lower_bound": -1.0,
                "upper_bound": 1.0,
                "init": 0.0,
                "scale": "linear"
            }
        },
        "optimizer_config": {
            "optimizer_type": "OnePlusOne",
            "budget": 100,
            "num_workers": 1
        },
        "execution_config": {
            "max_retries": 3,
            "timeout": 3600.0
        },
        "objective_fn": "def objective(x): return x**2"
    }

@pytest.fixture
def mock_task_queue():
    """Create a mock task queue."""
    queue = AsyncMock(spec=TaskQueue)
    queue.add_task = AsyncMock(return_value=None)
    
    # Create a proper task state
    task_state = {
        "task_id": "test-task",
        "status": "pending",
        "config": {
            "name": "test_task",
            "parameter_config": {
                "x": {
                    "lower_bound": -1.0,
                    "upper_bound": 1.0,
                    "init": 0.0,
                    "scale": "linear"
                }
            },
            "optimizer_config": {
                "optimizer_type": "OnePlusOne",
                "budget": 100,
                "num_workers": 1
            },
            "objective_fn": "def objective(x): return x**2"
        },
        "result": None,
        "error": None
    }
    
    queue.get_task = AsyncMock(return_value=task_state)
    queue.list_tasks = AsyncMock(return_value=[task_state])
    return queue

@pytest.fixture
def mock_websocket_manager():
    """Create a mock websocket manager."""
    manager = AsyncMock(spec=WebSocketManager)
    return manager

@pytest.fixture
def test_app(mock_task_queue, mock_websocket_manager):
    """Create a test FastAPI application."""
    app = FastAPI()
    app.include_router(router)
    app.dependency_overrides[get_task_queue] = lambda: mock_task_queue
    app.dependency_overrides[get_websocket_manager] = lambda: mock_websocket_manager
    return app

@pytest.fixture
def client(test_app):
    """Create a test client."""
    return TestClient(test_app)

def test_create_task(client, test_config, mock_task_queue):
    """Test task creation endpoint."""
    response = client.post("/tasks", json=test_config)
    print(f"Response: {response.json()}")  # Print response for debugging
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert "task_id" in data["data"]
    assert data["data"]["status"] == "pending"
    mock_task_queue.add_task.assert_called_once()

def test_get_task(client, mock_task_queue):
    """Test get task endpoint."""
    response = client.get("/tasks/test-task")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["data"]["task_id"] == "test-task"
    mock_task_queue.get_task.assert_called_once_with("test-task")

def test_list_tasks(client, mock_task_queue):
    """Test list tasks endpoint."""
    response = client.get("/tasks")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert len(data["data"]["tasks"]) == 1
    mock_task_queue.list_tasks.assert_called_once()

@pytest.mark.parametrize("action", ["pause", "resume", "stop"])
def test_task_control(client, mock_task_queue, action):
    """Test task control endpoints."""
    control_method = getattr(mock_task_queue, f"{action}_task")
    control_method.return_value = True
    
    response = client.post(f"/tasks/test-task/{action}")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    control_method.assert_called_once_with("test-task")

def test_task_control_failure(client, mock_task_queue):
    """Test task control failure handling."""
    mock_task_queue.pause_task.return_value = False
    mock_task_queue.get_task.return_value = {
        "task_id": "test-task",
        "status": "running",
        "config": {
            "name": "test_task",
            "parameter_config": {
                "x": {
                    "lower_bound": -1.0,
                    "upper_bound": 1.0,
                    "init": 0.0,
                    "scale": "linear"
                }
            },
            "optimizer_config": {
                "optimizer_type": "OnePlusOne",
                "budget": 100,
                "num_workers": 1
            },
            "objective_fn": "def objective(x): return x**2"
        },
        "result": None,
        "error": None
    }
    
    response = client.post("/tasks/test-task/pause")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "error"
    assert "message" in data["error"]

def test_websocket_endpoint(test_app, mock_websocket_manager):
    """Test WebSocket endpoint."""
    with TestClient(test_app) as client:
        with client.websocket_connect("/ws") as websocket:
            # Send a test message
            message = {"type": "test", "data": {"message": "test"}}
            websocket.send_json(message)
            
            # Verify the message was broadcast
            mock_websocket_manager.broadcast.assert_called_once_with(message) 