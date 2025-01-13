"""Example of using the task queue with a dummy optimization problem."""
import asyncio
import inspect
import time
import uuid
from typing import Dict, Any
from quantum_opt.queue import OptimizationTask
from quantum_opt.web import run_servers

def create_dummy_optimization(problem_id: int):
    """Create a dummy optimization task with a simple quadratic objective function."""
    # Define parameter configuration
    parameter_config = {
        "x": {
            "type": "scalar",
            "init": 0.0,
            "lower": -5.0,
            "upper": 5.0,
            "description": "X coordinate"
        },
        "y": {
            "type": "scalar",
            "init": 0.0,
            "lower": -5.0,
            "upper": 5.0,
            "description": "Y coordinate"
        }
    }
    
    # Define objective function that includes a delay for debugging
    def objective_function(params: Dict[str, float]) -> float:
        time.sleep(0.3)  # Add delay for debugging
        x, y = params["x"], params["y"]
        # Target is (problem_id, problem_id)
        return (x - problem_id)**2 + (y - problem_id)**2

    # Get source code of the objective function for web display
    source_code = inspect.getsource(objective_function)
    
    # Create task with unique name and configuration
    task = OptimizationTask(
        task_id=str(uuid.uuid4()),  # Generate unique task ID
        name=f"Dummy Problem {problem_id}",
        parameter_config=parameter_config,
        objective_function=objective_function,
        optimizer_config={
            "optimizer": "CMA",
            "budget": 20,  # Reduced budget for testing
            "num_workers": 2  # Reduced workers for testing
        },
        execution_config={
            "max_workers": 2,
            "checkpoint_dir": f"./checkpoints/problem_{problem_id}",
            "log_file": f"./logs/problem_{problem_id}.log",
            "log_level": "INFO"
        },
        source_code=source_code
    )
    
    return task

async def main():
    """Create multiple optimization tasks and start the web interface."""
    # Create tasks for different problem IDs
    tasks = [create_dummy_optimization(i) for i in range(3)]
    print(f"Created {len(tasks)} optimization tasks with 0.3s delay for debugging")
    
    # Start web interface with tasks
    await run_servers(tasks=tasks)

if __name__ == "__main__":
    asyncio.run(main()) 