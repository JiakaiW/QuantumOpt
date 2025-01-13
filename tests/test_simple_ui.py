"""Tests for the simple UI implementation."""
import asyncio
import logging
import pytest
import pytest_asyncio
from typing import AsyncGenerator
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.testclient import TestClient
from httpx import AsyncClient
from playwright.async_api import Page
import time
from fastapi.websockets import WebSocketDisconnect

from quantum_opt.queue import TaskQueue
from quantum_opt.web.backend.websocket_manager import WebSocketManager
from quantum_opt.web.backend.main import app
from quantum_opt.web.backend.dependencies import get_task_queue, get_websocket_manager

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('test_optimization.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

@pytest_asyncio.fixture
async def test_app() -> AsyncGenerator[FastAPI, None]:
    """Create a test app with initialized dependencies."""
    logger.info("Setting up test app")
    # Create fresh instances for each test
    task_queue = TaskQueue()
    websocket_manager = WebSocketManager()
    websocket_manager.initialize_queue(task_queue)
    
    # Override dependencies
    app.dependency_overrides[get_task_queue] = lambda: task_queue
    app.dependency_overrides[get_websocket_manager] = lambda: websocket_manager
    
    # Start task queue processing
    logger.info("Starting task queue processing")
    await task_queue.start_processing()
    
    try:
        yield app
    finally:
        logger.info("Cleaning up test app")
        await task_queue.stop_processing()
        app.dependency_overrides.clear()

@pytest.mark.asyncio
async def test_optimization_workflow(test_app: FastAPI):
    """Test the complete optimization workflow."""
    client = TestClient(test_app)
    logger.info("Starting optimization workflow test")
    
    # Create task
    logger.info("Creating optimization task")
    response = client.post(
        "/api/v1/tasks",
        json={
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
            "objective_fn": "def objective(x, y): return (x - 1)**2 + (y - 1)**2"
        }
    )
    assert response.status_code == 200, f"Failed to create task: {response.json()}"
    task_id = response.json()["data"]["task_id"]
    logger.info(f"Created task with ID: {task_id}")
    
    # Connect to WebSocket for updates
    logger.info("Connecting to WebSocket")
    try:
        with client.websocket_connect("/api/v1/ws") as websocket:
            # Start optimization
            logger.info(f"Starting optimization for task {task_id}")
            response = client.post(f"/api/v1/tasks/{task_id}/start")
            assert response.status_code == 200, f"Failed to start task: {response.json()}"
            
            # Wait for optimization to complete with timeout
            logger.info("Waiting for optimization to complete")
            start_time = time.time()
            timeout = 30  # 30 seconds timeout
            
            while True:
                if time.time() - start_time > timeout:
                    raise TimeoutError("Optimization timed out")
                
                try:
                    data = websocket.receive_json(timeout=1.0)  # 1 second timeout for each receive
                    logger.debug(f"Received WebSocket message: {data}")
                    
                    if "data" not in data:
                        logger.warning(f"Unexpected message format: {data}")
                        continue
                        
                    if "type" not in data["data"]:
                        logger.warning(f"Message missing type: {data}")
                        continue
                        
                    event_type = data["data"]["type"]
                    logger.debug(f"Received event type: {event_type}")
                    
                    if event_type == "TASK_COMPLETED":
                        received_task_id = data["data"].get("task_id")
                        if received_task_id == task_id:
                            logger.info(f"Task {task_id} completed")
                            break
                        else:
                            logger.warning(f"Received completion for different task: {received_task_id}")
                    elif event_type == "TASK_FAILED":
                        logger.error(f"Task failed: {data}")
                        assert False, f"Task failed: {data['data'].get('error', 'Unknown error')}"
                    elif event_type == "TASK_PROGRESS":
                        logger.debug(f"Task progress: {data['data'].get('progress', 'No progress info')}")
                    
                except WebSocketDisconnect:
                    logger.error("WebSocket disconnected unexpectedly")
                    raise
                except Exception as e:
                    logger.error(f"Error receiving WebSocket message: {e}", exc_info=True)
                    raise
            
            # Get final results
            logger.info(f"Getting final results for task {task_id}")
            response = client.get(f"/api/v1/tasks/{task_id}")
            assert response.status_code == 200, f"Failed to get task results: {response.json()}"
            result = response.json()["data"]
            
            # Verify results
            logger.info("Verifying optimization results")
            assert result["status"] == "completed", f"Task not completed. Status: {result['status']}"
            assert "parameters" in result, "No parameters in result"
            parameters = result["parameters"]
            assert "x" in parameters and "y" in parameters, f"Missing parameters in result: {parameters}"
            
            # Check convergence
            x, y = parameters["x"], parameters["y"]
            distance = ((x - 1.0) ** 2 + (y - 1.0) ** 2) ** 0.5
            logger.info(f"Final distance from minimum: {distance}")
            assert distance < 0.1, f"Did not converge to minimum. Distance: {distance}"
            
    except Exception as e:
        logger.error("Test failed with error", exc_info=True)
        raise 