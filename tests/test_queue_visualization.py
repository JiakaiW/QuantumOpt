"""Tests for optimization visualization."""
import pytest_asyncio
import logging
import uuid
from typing import AsyncGenerator, Dict, Any
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi.websockets import WebSocket
from quantum_opt.queue import TaskQueue
from quantum_opt.web.backend.websocket_manager import WebSocketManager
from quantum_opt.web.backend.dependencies import get_task_queue, get_websocket_manager
import time
import asyncio
import json
from quantum_opt.web.backend.api.v1.router import router as api_router
from quantum_opt.web.backend.api.v1.ws import router as ws_router

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('test_optimization.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def create_quadratic_objective() -> Dict[str, Any]:
    """Create a simple quadratic optimization task config."""
    return {
        "name": "test_quadratic",
        "parameter_config": {
            "x": {
                "lower_bound": -5.0,
                "upper_bound": 5.0,
                "scale": "linear"
            },
            "y": {
                "lower_bound": -5.0,
                "upper_bound": 5.0,
                "scale": "linear"
            }
        },
        "optimizer_config": {
            "optimizer_type": "CMA",
            "budget": 100,
            "num_workers": 4
        },
        "execution_config": {
            "max_retries": 3,
            "timeout": 3600
        },
        "objective_fn": """def objective(x, y):
    return (x - 1)**2 + (y - 1)**2"""
    }

@pytest_asyncio.fixture
async def task_queue() -> AsyncGenerator[TaskQueue, None]:
    """Create a fresh TaskQueue instance for each test."""
    queue = TaskQueue()
    await queue.start_processing()  # Start processing tasks
    yield queue
    await queue.stop_processing()  # Stop processing tasks

@pytest_asyncio.fixture
async def websocket_manager(task_queue: TaskQueue) -> AsyncGenerator[WebSocketManager, None]:
    """Create a WebSocketManager instance for each test."""
    manager = WebSocketManager()
    manager.initialize_queue(task_queue)
    yield manager

@pytest_asyncio.fixture
async def test_app(task_queue: TaskQueue, websocket_manager: WebSocketManager) -> AsyncGenerator[FastAPI, None]:
    """Create a FastAPI test application."""
    app = FastAPI()
    app.dependency_overrides[get_task_queue] = lambda: task_queue
    app.dependency_overrides[get_websocket_manager] = lambda: websocket_manager
    app.include_router(api_router, prefix="/api/v1")
    app.include_router(ws_router, prefix="/api/v1/ws")  # Include WebSocket router with correct prefix
    yield app

@pytest_asyncio.fixture
async def test_client(test_app: FastAPI) -> AsyncGenerator[TestClient, None]:
    """Create a test client."""
    client = TestClient(test_app)
    yield client

@pytest.mark.asyncio
@pytest.mark.timeout(10)  # 10 second timeout for the entire test
async def test_optimization_with_websocket(test_client: TestClient, test_app: FastAPI) -> None:
    """Test optimization with WebSocket updates and task control."""
    # Create and submit task
    task_config = create_quadratic_objective()
    response = test_client.post("/api/v1/tasks", json=task_config)
    assert response.status_code == 200
    task_id = response.json()["data"]["task_id"]
    logger.info(f"Created task with ID: {task_id}")

    # Generate a client ID for WebSocket connection
    client_id = str(uuid.uuid4())
    logger.info(f"Using client ID: {client_id}")

    # Connect to WebSocket with client ID
    with test_client.websocket_connect(f"/api/v1/ws/queue?client_id={client_id}") as websocket:
        # Start optimization
        response = test_client.post(f"/api/v1/tasks/{task_id}/start")
        assert response.status_code == 200
        logger.info("Started task")

        # Track optimization progress
        start_time = time.time()
        best_value = float('inf')
        iteration_count = 0
        
        while time.time() - start_time < 10:  # 10 second timeout
            try:
                # Use asyncio timeout for receiving messages
                try:
                    async with asyncio.timeout(5.0):  # 5 second timeout for each message
                        message = websocket.receive_json()
                except asyncio.TimeoutError:
                    logger.error("Timeout waiting for WebSocket message")
                    raise

                logger.debug(f"Received WebSocket message: {message}")
                
                if "data" not in message:
                    continue
                    
                event_data = message["data"]
                event_type = event_data.get("type")
                
                if event_type == "TASK_STATUS_CHANGED":
                    status = event_data.get("status")
                    logger.info(f"Task status changed to: {status}")
                    
                    if status == "completed":
                        # Verify final result
                        response = test_client.get(f"/api/v1/tasks/{task_id}")
                        assert response.status_code == 200
                        task_state = response.json()["data"]
                        result = task_state["result"]
                        assert "best_params" in result
                        best_params = result["best_params"]
                        distance = ((best_params["x"] - 1)**2 + (best_params["y"] - 1)**2)**0.5
                        assert distance < 0.1, f"Optimization did not converge. Distance from minimum: {distance}"
                        logger.info("Task completed successfully")
                        return
                    elif status == "failed":
                        error = event_data.get("error", "Unknown error")
                        logger.error(f"Task failed: {error}")
                        assert False, f"Task failed: {error}"
                        
                elif event_type == "ITERATION_COMPLETED":
                    # Track optimization progress
                    iteration_data = event_data.get("data", {})
                    current_value = iteration_data.get("best_value")
                    if current_value is not None:
                        best_value = min(best_value, current_value)
                        iteration_count += 1
                        logger.info(f"Iteration {iteration_count}: best value = {best_value}")
                        
                        # Test pause/resume functionality after a few iterations
                        if iteration_count == 2:
                            # Pause optimization
                            response = test_client.post(f"/api/v1/tasks/{task_id}/pause")
                            assert response.status_code == 200
                            logger.info("Paused task")
                            
                            # Wait a bit
                            await asyncio.sleep(1)
                            
                            # Resume optimization
                            response = test_client.post(f"/api/v1/tasks/{task_id}/resume")
                            assert response.status_code == 200
                            logger.info("Resumed task")
                
            except Exception as e:
                logger.error(f"Error processing WebSocket message: {e}")
                raise

        assert False, "Optimization did not complete within timeout"

@pytest.mark.asyncio
@pytest.mark.timeout(7)  # 7 second timeout for the control test
async def test_optimization_control(test_client: TestClient) -> None:
    """Test task control operations."""
    # Create task
    task_config = create_quadratic_objective()
    response = test_client.post("/api/v1/tasks", json=task_config)
    assert response.status_code == 200
    task_id = response.json()["data"]["task_id"]
    logger.info(f"Created task with ID: {task_id}")

    # Test start
    response = test_client.post(f"/api/v1/tasks/{task_id}/start")
    assert response.status_code == 200
    logger.info("Started task")

    # Wait for task to start running
    start_time = time.time()
    while time.time() - start_time < 5:
        response = test_client.get(f"/api/v1/tasks/{task_id}")
        assert response.status_code == 200
        task_state = response.json()["data"]
        if task_state["status"] == "running":
            break
        await asyncio.sleep(0.1)
    else:
        assert False, "Task did not start running within timeout"

    # Test pause
    response = test_client.post(f"/api/v1/tasks/{task_id}/pause")
    assert response.status_code == 200
    logger.info("Paused task")

    # Verify paused state
    response = test_client.get(f"/api/v1/tasks/{task_id}")
    assert response.status_code == 200
    task_state = response.json()["data"]
    assert task_state["status"] == "paused", "Task should be paused"

    # Test resume
    response = test_client.post(f"/api/v1/tasks/{task_id}/resume")
    assert response.status_code == 200
    logger.info("Resumed task")

    # Verify running state
    response = test_client.get(f"/api/v1/tasks/{task_id}")
    assert response.status_code == 200
    task_state = response.json()["data"]
    assert task_state["status"] == "running", "Task should be running"

    # Test stop
    response = test_client.post(f"/api/v1/tasks/{task_id}/stop")
    assert response.status_code == 200
    logger.info("Stopped task")

    # Verify stopped state
    response = test_client.get(f"/api/v1/tasks/{task_id}")
    assert response.status_code == 200
    task_state = response.json()["data"]
    assert task_state["status"] == "stopped", "Task should be stopped" 