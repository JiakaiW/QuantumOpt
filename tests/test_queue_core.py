"""Test core queue functionality with a simple optimization example.

This test focuses on:
1. Basic task creation
2. Task execution
3. Progress monitoring
4. Result verification

No web/visualization dependencies are used.
"""
import asyncio
import pytest
from typing import Dict, Any

from quantum_opt.queue.task import OptimizationTask
from quantum_opt.queue.manager import TaskQueue
from quantum_opt.optimizers.optimization_schemas import (
    OptimizationConfig,
    ParameterConfig,
    OptimizerConfig
)

def create_quadratic_config() -> Dict[str, Any]:
    """Create a configuration for optimizing a simple quadratic function."""
    # Define the objective function
    objective_fn = """def objective(x: float, y: float) -> float:
    \"\"\"Quadratic function with minimum at (1, 1).\"\"\"
    return (x - 1.0)**2 + (y - 1.0)**2
"""
    
    # Create optimization configuration
    config = OptimizationConfig(
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
            budget=10,  # Reduced for testing
            num_workers=1   # Single worker for simpler testing
        ),
        objective_fn=objective_fn,
        objective_fn_source=objective_fn
    )
    
    return config.model_dump()

async def monitor_progress(queue: TaskQueue, task_id: str, timeout: float = 10.0) -> Dict[str, Any]:
    """Monitor task progress and return final results."""
    results = []
    start_time = asyncio.get_event_loop().time()
    
    while True:
        # Check timeout
        if asyncio.get_event_loop().time() - start_time > timeout:
            raise TimeoutError(f"Task {task_id} did not complete within {timeout} seconds")
        
        # Get task state
        task_state = await queue.get_task(task_id)
        if not task_state:
            await asyncio.sleep(0.1)
            continue
            
        status = task_state["status"]
        if status == "completed":
            return task_state["result"]
        elif status == "failed":
            raise RuntimeError(f"Task {task_id} failed: {task_state.get('error')}")
        elif status == "running":
            # Get latest progress
            if task_state.get("result"):
                current_result = task_state["result"]
                results.append(current_result)
                print(f"Iteration {len(results)}: value = {current_result.get('best_value', 'N/A')}")
        
        await asyncio.sleep(0.1)  # Avoid busy waiting

@pytest.mark.asyncio
async def test_quadratic_optimization():
    """Test optimization of a simple quadratic function using the queue."""
    # Create queue manager
    queue = TaskQueue()
    
    try:
        # Create and submit task configuration
        config = create_quadratic_config()
        await queue.add_task(config)
        
        # Get task ID from the first task in the queue
        tasks = await queue.list_tasks()
        assert len(tasks) > 0, "No tasks in queue"
        task_id = tasks[0]["task_id"]
        
        # Start queue processing
        await queue.start_processing()
        
        # Monitor progress and get results with timeout
        try:
            results = await monitor_progress(queue, task_id, timeout=30.0)
        except TimeoutError as e:
            await queue.stop_processing()
            pytest.fail(str(e))
        
        # Verify results
        assert results is not None, "No results returned"
        assert "best_params" in results, "No best parameters in results"
        assert "best_value" in results, "No best value in results"
        
        best_params = results["best_params"]
        best_value = results["best_value"]
        
        print("\nOptimization Results:")
        print(f"Best parameters: x = {best_params['x']:.6f}, y = {best_params['y']:.6f}")
        print(f"Best value: {best_value:.6f}")
        
        # Check convergence to known minimum at (1, 1)
        assert abs(best_params["x"] - 1.0) < 0.1, f"x did not converge to minimum: {best_params['x']}"
        assert abs(best_params["y"] - 1.0) < 0.1, f"y did not converge to minimum: {best_params['y']}"
        assert best_value < 0.01, f"Function value did not reach minimum: {best_value}"
        
    finally:
        # Clean up
        await queue.stop_processing()

if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 