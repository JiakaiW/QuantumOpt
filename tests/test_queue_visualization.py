"""Simple example of optimization visualization.

This example demonstrates:
1. Basic task creation
2. Real-time monitoring
3. Simple visualization
"""
import asyncio
import logging
from typing import AsyncGenerator
from fastapi.testclient import TestClient
import pytest
from fastapi import FastAPI

from quantum_opt.optimizers.optimization_schemas import (
    OptimizationConfig,
    ParameterConfig,
    OptimizerConfig
)
from quantum_opt.web.backend.main import app
from quantum_opt.web.backend.dependencies import get_task_queue, get_websocket_manager
from quantum_opt.web.backend.task_queue import TaskQueue
from quantum_opt.web.backend.websocket_manager import WebSocketManager

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_quadratic_objective() -> str:
    """Create a simple quadratic objective function with minimum at (1, 1)."""
    return """def objective(x: float, y: float) -> float:
    \"\"\"Quadratic function with minimum at (1, 1).\"\"\"
    return (x - 1.0)**2 + (y - 1.0)**2
"""

def create_optimization_config() -> OptimizationConfig:
    """Create a simple optimization configuration."""
    objective_fn = create_quadratic_objective()
    
    return OptimizationConfig(
        name="Simple Quadratic",
        parameter_config={
            "x": ParameterConfig(
                lower_bound=-5.0,
                upper_bound=5.0,
                init=0.0,
                scale="linear"
            ),
            "y": ParameterConfig(
                lower_bound=-5.0,
                upper_bound=5.0,
                init=0.0,
                scale="linear"
            )
        },
        optimizer_config=OptimizerConfig(
            optimizer_type="CMA",
            budget=50,
            num_workers=4
        ),
        objective_fn=objective_fn,
        objective_fn_source=objective_fn
    )

@pytest.fixture
async def initialized_app() -> AsyncGenerator[FastAPI, None]:
    """Create and initialize the FastAPI application with dependencies."""
    # Create fresh instances for each test
    task_queue = TaskQueue()
    websocket_manager = WebSocketManager()
    
    # Override the dependency providers
    app.dependency_overrides[get_task_queue] = lambda: task_queue
    app.dependency_overrides[get_websocket_manager] = lambda: websocket_manager
    
    # Initialize WebSocket manager with task queue
    websocket_manager.initialize_queue(task_queue)
    
    yield app
    
    # Cleanup
    app.dependency_overrides.clear()

@pytest.fixture
def test_client(initialized_app: FastAPI) -> TestClient:
    """Create a test client with initialized dependencies."""
    return TestClient(initialized_app)

@pytest.mark.asyncio
async def test_basic_optimization(test_client: TestClient):
    """Test basic optimization with visualization."""
    # Create and submit optimization task
    config = create_optimization_config()
    response = test_client.post("/api/v1/tasks", json=config.model_dump())
    assert response.status_code == 200, f"Failed to create task: {response.json()}"
    task_id = response.json()["data"]["task_id"]
    
    # Start optimization
    response = test_client.post("/api/v1/queue/control", json={"action": "start"})
    assert response.status_code == 200, f"Failed to start optimization: {response.json()}"
    
    # Monitor progress
    progress = []
    completed = False
    timeout = 30  # seconds
    start_time = asyncio.get_event_loop().time()
    
    try:
        with test_client.websocket_connect("/api/v1/ws") as websocket:
            logger.info("WebSocket connection established")
            
            # Monitor optimization progress
            while not completed and (asyncio.get_event_loop().time() - start_time) < timeout:
                try:
                    data = websocket.receive_json()
                    logger.debug(f"Received WebSocket data: {data}")
                    
                    if not isinstance(data, dict):
                        logger.warning(f"Unexpected WebSocket data format: {data}")
                        continue
                        
                    if data.get("status") != "success":
                        logger.warning(f"Unsuccessful WebSocket message: {data}")
                        continue
                    
                    event = data.get("data", {})
                    if not isinstance(event, dict):
                        continue
                        
                    event_type = event.get("type")
                    if event_type == "ITERATION_COMPLETED" and event.get("task_id") == task_id:
                        best_x = event.get("best_x", {})
                        current_progress = {
                            'iteration': len(progress),
                            'value': event.get("best_y"),
                            'x': best_x.get("x"),
                            'y': best_x.get("y")
                        }
                        progress.append(current_progress)
                        
                        logger.info(
                            f"Iteration {current_progress['iteration']}: "
                            f"f({current_progress['x']:.3f}, {current_progress['y']:.3f}) = "
                            f"{current_progress['value']:.6f}"
                        )
                            
                    elif event_type == "TASK_COMPLETED" and event.get("task_id") == task_id:
                        completed = True
                        
                        # Get final results
                        response = test_client.get(f"/api/v1/tasks/{task_id}")
                        assert response.status_code == 200, f"Failed to get task results: {response.json()}"
                        result = response.json()["data"]["result"]
                        
                        logger.info("\nOptimization Results:")
                        logger.info(
                            f"Best parameters: x = {result['best_params']['x']:.6f}, "
                            f"y = {result['best_params']['y']:.6f}"
                        )
                        logger.info(f"Best value: {result['best_value']:.6f}")
                        logger.info(f"Total evaluations: {result['total_evaluations']}")
                        
                        # Verify convergence
                        assert abs(result['best_params']['x'] - 1.0) < 0.1, "x did not converge to minimum"
                        assert abs(result['best_params']['y'] - 1.0) < 0.1, "y did not converge to minimum"
                        assert result['best_value'] < 0.01, "function value did not reach minimum"
                        break
                        
                except Exception as e:
                    logger.error(f"Error processing WebSocket message: {e}")
                    continue
                    
    except Exception as e:
        logger.error(f"WebSocket connection error: {e}")
        raise
        
    assert completed, "Optimization did not complete within timeout"
    assert len(progress) > 0, "No optimization progress was recorded"

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--log-cli-level=INFO"]) 