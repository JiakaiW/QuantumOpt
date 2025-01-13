"""Test web API endpoints for task management.

This test focuses on:
1. Task submission
2. Status checking
3. Basic control (start/stop)
4. Real-time updates via WebSocket
"""
import asyncio
import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from fastapi import FastAPI
from typing import Dict, Any, AsyncGenerator

from quantum_opt.web.backend.main import app
from quantum_opt.web.backend.dependencies import get_task_queue, get_websocket_manager
from quantum_opt.queue.task import OptimizationTask
from quantum_opt.queue.manager import TaskQueue
from quantum_opt.web.backend.websocket_manager import WebSocketManager

def create_quadratic_config() -> Dict[str, Any]:
    """Create a configuration for optimizing a simple quadratic function."""
    return {
        "name": "Simple Quadratic",
        "parameter_config": {
            "x": {
                "lower_bound": -5.0,
                "upper_bound": 5.0,
                "init": 0.0,
                "scale": "linear"
            },
            "y": {
                "lower_bound": -5.0,
                "upper_bound": 5.0,
                "init": 0.0,
                "scale": "linear"
            }
        },
        "optimizer_config": {
            "optimizer_type": "CMA",
            "budget": 10,
            "num_workers": 1
        },
        "objective_fn": """def objective(x: float, y: float) -> float:
    \"\"\"Quadratic function with minimum at (1, 1).\"\"\"
    return (x - 1.0)**2 + (y - 1.0)**2
""",
        "objective_fn_source": None
    }

@pytest_asyncio.fixture
async def task_queue() -> AsyncGenerator[TaskQueue, None]:
    """Create a task queue for testing."""
    queue = TaskQueue()
    yield queue
    await queue.stop_processing()

@pytest_asyncio.fixture
async def websocket_manager(task_queue: TaskQueue) -> WebSocketManager:
    """Create a WebSocket manager for testing."""
    manager = WebSocketManager()
    manager.initialize_queue(task_queue)
    return manager

@pytest.fixture
def test_client(task_queue: TaskQueue, websocket_manager: WebSocketManager) -> TestClient:
    """Create a test client with initialized dependencies."""
    app.dependency_overrides[get_task_queue] = lambda: task_queue
    app.dependency_overrides[get_websocket_manager] = lambda: websocket_manager
    
    client = TestClient(app)
    
    yield client
    
    app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_task_lifecycle(test_client: TestClient):
    """Test complete task lifecycle through API endpoints."""
    # Create task
    config = create_quadratic_config()
    response = test_client.post("/api/v1/tasks", json=config)
    assert response.status_code == 200, f"Failed to create task: {response.json()}"
    data = response.json()["data"]
    task_id = data["task_id"]
    
    # Verify task was created
    response = test_client.get(f"/api/v1/tasks/{task_id}")
    assert response.status_code == 200, f"Failed to get task: {response.json()}"
    assert response.json()["data"]["status"] == "pending"
    
    # Start optimization
    response = test_client.post("/api/v1/queue/control", json={"action": "start"})
    assert response.status_code == 200, f"Failed to start optimization: {response.json()}"
    
    # Monitor progress via WebSocket
    progress_received = False
    completion_received = False
    
    with test_client.websocket_connect("/api/v1/ws") as websocket:
        # Wait for initial state message
        data = websocket.receive_json()
        assert data["status"] == "success"
        assert data["data"]["type"] == "INITIAL_STATE"
        
        # Monitor progress
        timeout = 30  # seconds
        start_time = asyncio.get_event_loop().time()
        
        while not completion_received and (asyncio.get_event_loop().time() - start_time) < timeout:
            data = websocket.receive_json()
            assert data["status"] == "success"
            
            event = data["data"]
            if event["type"] == "ITERATION_COMPLETED" and event["task_id"] == task_id:
                progress_received = True
                print(f"Progress: value = {event.get('best_y', 'N/A')}")
            elif event["type"] == "TASK_COMPLETED" and event["task_id"] == task_id:
                completion_received = True
                break
    
    # Verify progress was received
    assert progress_received, "No progress updates received"
    assert completion_received, "Task did not complete"
    
    # Get final results
    response = test_client.get(f"/api/v1/tasks/{task_id}")
    assert response.status_code == 200, f"Failed to get results: {response.json()}"
    result = response.json()["data"]["result"]
    
    # Verify convergence
    assert abs(result["best_params"]["x"] - 1.0) < 0.1, "x did not converge to minimum"
    assert abs(result["best_params"]["y"] - 1.0) < 0.1, "y did not converge to minimum"
    assert result["best_value"] < 0.01, "Function value did not reach minimum"

@pytest.mark.asyncio
async def test_task_control(test_client: TestClient):
    """Test task control operations (pause/resume/stop)."""
    # Create task
    config = create_quadratic_config()
    response = test_client.post("/api/v1/tasks", json=config)
    assert response.status_code == 200
    task_id = response.json()["data"]["task_id"]
    
    # Start optimization
    response = test_client.post("/api/v1/queue/control", json={"action": "start"})
    assert response.status_code == 200
    
    # Wait for task to start
    await asyncio.sleep(0.5)
    
    # Get task status
    response = test_client.get(f"/api/v1/tasks/{task_id}")
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "running"
    
    # Pause task
    response = test_client.post(f"/api/v1/tasks/{task_id}/pause")
    assert response.status_code == 200
    
    # Verify paused status
    response = test_client.get(f"/api/v1/tasks/{task_id}")
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "paused"
    
    # Resume task
    response = test_client.post(f"/api/v1/tasks/{task_id}/resume")
    assert response.status_code == 200
    
    # Verify running status
    response = test_client.get(f"/api/v1/tasks/{task_id}")
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "running"
    
    # Stop task
    response = test_client.post(f"/api/v1/tasks/{task_id}/stop")
    assert response.status_code == 200
    
    # Verify stopped status
    response = test_client.get(f"/api/v1/tasks/{task_id}")
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "stopped"

if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 