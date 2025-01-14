"""Integration test for QuantumOpt web interface."""
import pytest
import pytest_asyncio
import asyncio
import aiohttp
import json
from typing import Dict, Any, AsyncGenerator
from quantum_opt.web.backend.main import app
from quantum_opt.web.backend.api.dependencies import get_task_queue, get_websocket_manager
from quantum_opt.queue import TaskQueue
from quantum_opt.web.backend.websocket_manager import WebSocketManager
from fastapi.testclient import TestClient
from fastapi import FastAPI
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Test configuration
BASE_URL = "http://localhost:8000/api/v1"
WS_URL = "ws://localhost:8000/api/v1/ws"
TEST_TIMEOUT = 30  # 30 seconds timeout for tests
RECEIVE_TIMEOUT = 5.0  # 5 seconds timeout for receiving messages

# Test data
def create_test_task_config() -> Dict[str, Any]:
    """Create a test task configuration."""
    return {
        "name": "test_task",
        "parameter_config": {
            "x": {"lower_bound": -2.0, "upper_bound": 2.0, "init": 0.0},
            "y": {"lower_bound": -2.0, "upper_bound": 2.0, "init": 0.0}
        },
        "optimizer_config": {
            "optimizer_type": "CMA",
            "budget": 500,  # Increased from 200
            "num_workers": 1
        },
        "execution_config": {
            "max_retries": 3,
            "timeout": 30
        },
        "objective_fn": "def objective(x, y):\n    return (x - 1.0)**2 + (y - 1.0)**2"
    }

@pytest_asyncio.fixture
async def task_queue() -> AsyncGenerator[TaskQueue, None]:
    """Create a test task queue."""
    queue = TaskQueue()
    yield queue
    await queue.stop_processing()

@pytest_asyncio.fixture
async def websocket_manager(task_queue: TaskQueue) -> AsyncGenerator[WebSocketManager, None]:
    """Create a WebSocketManager instance."""
    manager = WebSocketManager()
    manager.initialize_queue(task_queue)
    await task_queue.start_processing()  # Start processing after initializing WebSocket manager
    yield manager
    # Close any remaining connections
    for client_id in list(manager._connections.keys()):
        try:
            await manager._connections[client_id].close()
        except:
            pass
    await task_queue.stop_processing()  # Clean up

@pytest.fixture
def test_app(task_queue: TaskQueue, websocket_manager: WebSocketManager) -> FastAPI:
    """Create a test FastAPI application."""
    app.dependency_overrides[get_task_queue] = lambda: task_queue
    app.dependency_overrides[get_websocket_manager] = lambda: websocket_manager
    return app

@pytest.fixture
def test_client(test_app: FastAPI) -> TestClient:
    """Create a test client."""
    return TestClient(test_app)

@pytest.mark.asyncio
@pytest.mark.timeout(TEST_TIMEOUT)
async def test_complete_workflow(
    test_client: TestClient,
    task_queue: TaskQueue,
    websocket_manager: WebSocketManager
):
    """Test the complete optimization workflow."""
    # 1. Create task
    config = create_test_task_config()
    response = test_client.post("/api/v1/tasks", json=config)
    assert response.status_code == 200
    task_data = response.json()
    assert task_data["status"] == "success"
    task_id = task_data["data"]["task_id"]
    
    # 2. Connect WebSocket
    async with aiohttp.ClientSession() as session:
        async with session.ws_connect(
            f"{WS_URL}?client_id=test_client",
            timeout=aiohttp.ClientWSTimeout(ws_close=RECEIVE_TIMEOUT)
        ) as ws:
            # Verify connection
            try:
                msg = await asyncio.wait_for(ws.receive_json(), timeout=RECEIVE_TIMEOUT)
                assert msg["status"] == "success"
                assert msg["data"]["type"] == "CONNECTED"
                
                # Get initial state
                msg = await asyncio.wait_for(ws.receive_json(), timeout=RECEIVE_TIMEOUT)
                assert msg["status"] == "success"
                assert msg["data"]["type"] == "INITIAL_STATE"
                
                # 3. Start task
                response = test_client.post(f"/api/v1/tasks/{task_id}/start")
                assert response.status_code == 200
                
                # 4. Monitor progress
                optimization_completed = False
                iteration_count = 0
                
                while not optimization_completed and iteration_count < 10:
                    try:
                        msg = await asyncio.wait_for(ws.receive_json(), timeout=RECEIVE_TIMEOUT)
                        if msg["status"] == "success":
                            if msg["data"]["type"] == "TASK_UPDATE":
                                if msg["data"]["event_type"] == "OPTIMIZATION_COMPLETED":
                                    optimization_completed = True
                                elif msg["data"]["event_type"] == "ITERATION_COMPLETED":
                                    iteration_count += 1
                                    
                                    # Test pause after a few iterations
                                    if iteration_count == 3:
                                        response = test_client.post(f"/api/v1/tasks/{task_id}/pause")
                                        assert response.status_code == 200
                                        
                                        # Wait briefly
                                        await asyncio.sleep(1)
                                        
                                        # Resume
                                        response = test_client.post(f"/api/v1/tasks/{task_id}/resume")
                                        assert response.status_code == 200
                    except asyncio.TimeoutError:
                        logger.warning("Timeout waiting for WebSocket message")
                        break
                
                # 5. Verify results
                response = test_client.get(f"/api/v1/tasks/{task_id}")
                assert response.status_code == 200
                task_state = response.json()
                assert task_state["status"] == "success"
                
                result = task_state["data"]["result"]
                if result:
                    assert "best_params" in result
                    assert "best_value" in result
                    # For quadratic function, should be close to 0
                    assert abs(result["best_value"]) < 1.0
                    
                    # Best parameters should be close to (1.0, 1.0)
                    best_x = result["best_params"]["x"]
                    best_y = result["best_params"]["y"]
                    assert abs(best_x - 1.0) < 0.5
                    assert abs(best_y - 1.0) < 0.5
            except asyncio.TimeoutError:
                logger.error("Test timed out waiting for WebSocket messages")
                raise
            finally:
                await ws.close()

if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 