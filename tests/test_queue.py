"""Tests for task queue functionality."""
import asyncio
import pytest
from typing import Dict, Any
from quantum_opt.queue.manager import TaskQueue
from quantum_opt.queue.task import OptimizationTask
from quantum_opt.utils.events import Event, EventType

@pytest.fixture
def task_config() -> Dict[str, Any]:
    """Create a test task configuration."""
    def objective_fn(x: float) -> float:
        """Simple objective function for testing."""
        return (x - 1) ** 2
        
    return {
        "name": "Test Task",
        "parameter_config": {
            "x": {
                "lower_bound": -5.0,
                "upper_bound": 5.0
            }
        },
        "optimizer_config": {
            "optimizer_type": "global",
            "budget": 10
        },
        "execution_config": {
            "timeout": 60.0,
            "max_retries": 3
        },
        "objective_fn": objective_fn
    }

@pytest.fixture
def optimization_task(task_config: Dict[str, Any]) -> OptimizationTask:
    """Create a test optimization task."""
    return OptimizationTask("test-task-1", task_config)

@pytest.fixture
def task_queue() -> TaskQueue:
    """Create a test task queue."""
    return TaskQueue()

@pytest.mark.asyncio
async def test_task_queue_add_task(task_queue: TaskQueue, optimization_task: OptimizationTask):
    """Test adding a task to the queue."""
    await task_queue.add_task(optimization_task)
    assert optimization_task.task_id in task_queue._tasks
    task = await task_queue.get_task(optimization_task.task_id)
    assert task == optimization_task

@pytest.mark.asyncio
async def test_task_queue_list_tasks(task_queue: TaskQueue, optimization_task: OptimizationTask):
    """Test listing tasks in the queue."""
    await task_queue.add_task(optimization_task)
    tasks = await task_queue.list_tasks()
    assert len(tasks) == 1
    assert tasks[0]["task_id"] == optimization_task.task_id

@pytest.mark.asyncio
async def test_task_state_transitions(task_queue: TaskQueue, optimization_task: OptimizationTask):
    """Test task state transitions."""
    await task_queue.add_task(optimization_task)
    assert optimization_task.status == "pending"
    
    # Start processing
    processing_task = asyncio.create_task(task_queue.start_processing())
    await asyncio.sleep(0.1)  # Allow time for processing to start
    assert optimization_task.status == "running"
    
    # Stop processing
    await task_queue.stop_task(optimization_task.task_id)
    assert optimization_task.status == "stopped"
    
    # Cleanup
    task_queue._stopped = True
    await processing_task

@pytest.mark.asyncio
async def test_task_event_notifications(task_queue: TaskQueue, optimization_task: OptimizationTask):
    """Test task event notifications."""
    events = []
    
    async def event_handler(event: Event):
        events.append(event)
    
    task_queue.add_subscriber(event_handler)
    await task_queue.add_task(optimization_task)
    
    assert len(events) == 1
    assert events[0].type == EventType.TASK_ADDED
    assert events[0].data["task_id"] == optimization_task.task_id

@pytest.mark.asyncio
async def test_task_error_handling(task_queue: TaskQueue, optimization_task: OptimizationTask):
    """Test task error handling."""
    # Simulate an error in the optimization
    optimization_task._optimizer = None  # This will cause an error when trying to start
    
    await task_queue.add_task(optimization_task)
    processing_task = asyncio.create_task(task_queue.start_processing())
    
    await asyncio.sleep(0.1)  # Allow time for processing
    assert optimization_task.status == "failed"
    
    # Cleanup
    task_queue._stopped = True
    await processing_task

@pytest.mark.asyncio
async def test_multiple_tasks_sequential_processing(task_queue: TaskQueue, task_config: Dict[str, Any]):
    """Test sequential processing of multiple tasks."""
    # Create multiple tasks
    tasks = [
        OptimizationTask(f"test-task-{i}", task_config)
        for i in range(3)
    ]
    
    # Add tasks to queue
    for task in tasks:
        await task_queue.add_task(task)
    
    # Start processing
    processing_task = asyncio.create_task(task_queue.start_processing())
    await asyncio.sleep(0.1)  # Allow time for first task to start
    
    # Verify first task is running
    assert tasks[0].status == "running"
    
    # Stop processing
    task_queue._stopped = True
    await processing_task

@pytest.mark.asyncio
async def test_task_queue_cleanup(task_queue: TaskQueue, optimization_task: OptimizationTask):
    """Test proper cleanup of tasks."""
    await task_queue.add_task(optimization_task)
    processing_task = asyncio.create_task(task_queue.start_processing())
    
    await asyncio.sleep(0.1)  # Allow time for processing to start
    await task_queue.stop_task(optimization_task.task_id)
    
    assert optimization_task._optimizer is None
    task_queue._stopped = True
    await processing_task 