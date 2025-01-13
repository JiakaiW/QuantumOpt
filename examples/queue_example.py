"""Example script demonstrating the task queue and web interface.

This example creates multiple optimization tasks with a dummy objective function
that has a known minimum. Each task is processed sequentially, but evaluations
within a task are parallelized. The web interface shows real-time progress.
"""

import asyncio
import inspect
import logging
import time
import uuid
from pathlib import Path
from typing import Dict, Any, Callable

from quantum_opt.queue import OptimizationTask
from quantum_opt.web import run_servers

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Create directories for logs and checkpoints
CHECKPOINT_DIR = Path("./checkpoints")
LOG_DIR = Path("./logs")
CHECKPOINT_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

def create_dummy_optimization(problem_id: int) -> OptimizationTask:
    """Create a dummy optimization task.
    
    The objective function is a simple quadratic function with a minimum at
    (problem_id, problem_id). This allows us to verify that the optimization
    is working correctly by checking if it finds the known minimum.
    """
    # Define parameter configuration
    parameter_config = {
        "x": {
            "type": "scalar",
            "init": 0.0,
            "lower": -5.0,
            "upper": 5.0,
            "description": "x coordinate"
        },
        "y": {
            "type": "scalar",
            "init": 0.0,
            "lower": -5.0,
            "upper": 5.0,
            "description": "y coordinate"
        }
    }
    
    def objective_function(params: Dict[str, float]) -> float:
        """Objective function with a known minimum at (problem_id, problem_id).
        
        Adds a small delay to simulate computation time and ensure we can
        see the optimization progress in the web interface.
        """
        time.sleep(0.3)  # Add delay for debugging
        x, y = params["x"], params["y"]
        # Add small offset to avoid zero and make log scale look better
        return ((x - problem_id)**2 + (y - problem_id)**2) + 1e-6
    
    # Get source code of the objective function for display
    source_code = inspect.getsource(objective_function)
    
    task = OptimizationTask(
        task_id=str(uuid.uuid4()),
        name=f"Dummy Problem {problem_id}",
        parameter_config=parameter_config,
        objective_function=objective_function,
        optimizer_config={
            "budget": 10,  # Small budget for testing
        },
        execution_config={
            "max_workers": 1,
            "checkpoint_dir": str(CHECKPOINT_DIR / f"problem_{problem_id}"),
            "log_file": str(LOG_DIR / f"problem_{problem_id}.log"),
            "log_level": "INFO",
            "precompile": True
        },
        source_code=source_code
    )
    logger.debug(f"Created task {task.task_id} for problem {problem_id}")
    return task

async def main():
    """Run example with multiple optimization tasks."""
    
    # Create three optimization tasks with different target minima
    tasks = [
        create_dummy_optimization(problem_id)
        for problem_id in range(3)
    ]
    logger.debug(f"Created {len(tasks)} tasks")
    
    # Run the servers with our tasks
    logger.debug("Starting servers with tasks")
    await run_servers(tasks=tasks, dev_mode=True)

if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main()) 