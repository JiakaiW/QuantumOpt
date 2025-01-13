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
    return {
        "name": "Test Task",
        "parameter_config": {
            "x": {
                "lower_bound": -5.0,
                "upper_bound": 5.0,
                "init": 0.0,
                "scale": "linear"
            }
        },
        "optimizer_config": {
            "optimizer_type": "OnePlusOne",
            "budget": 10,
            "num_workers": 1
        },
        "execution_config": {
            "timeout": 60.0,
            "max_retries": 3
        },
        "objective_fn": "def objective(x):\n    return (x - 1) ** 2"
    }

@pytest.fixture
def task_queue() -> TaskQueue:
    """Create a test task queue."""
    return TaskQueue()

@pytest.mark.asyncio
async def test_add_task_with_string_objective(task_queue: TaskQueue, task_config: Dict[str, Any]):
    """Test adding a task with string-based objective function."""
    await task_queue.add_task(task_config)
    tasks = await task_queue.list_tasks()
    assert len(tasks) == 1
    task = tasks[0]
    assert task["config"]["objective_fn"] == task_config["objective_fn"]
    assert task["status"] == "pending"

@pytest.mark.asyncio
async def test_add_task_with_invalid_objective(task_queue: TaskQueue, task_config: Dict[str, Any]):
    """Test adding a task with invalid objective function."""
    # Test with syntax error
    task_config["objective_fn"] = "def objective(x: return x"
    await task_queue.add_task(task_config)
    tasks = await task_queue.list_tasks()
    assert len(tasks) == 1
    task = tasks[0]
    assert task["status"] == "failed"
    assert "Invalid objective function" in task["error"]

    # Test with wrong function name
    task_config["objective_fn"] = "def wrong_name(x):\n    return x**2"
    await task_queue.add_task(task_config)
    tasks = await task_queue.list_tasks()
    assert len(tasks) == 2
    task = tasks[1]
    assert task["status"] == "failed"
    assert "Function must be named 'objective'" in task["error"]

@pytest.mark.asyncio
async def test_add_task_with_parameter_mismatch(task_queue: TaskQueue, task_config: Dict[str, Any]):
    """Test adding a task with parameter mismatch."""
    task_config["objective_fn"] = "def objective(wrong_param):\n    return wrong_param**2"
    await task_queue.add_task(task_config)
    tasks = await task_queue.list_tasks()
    assert len(tasks) == 1
    task = tasks[0]
    assert task["status"] == "failed"
    assert "parameters ['wrong_param'] don't match config parameters ['x']" in task["error"]

@pytest.mark.asyncio
async def test_task_execution(task_queue: TaskQueue, task_config: Dict[str, Any]):
    """Test task execution with string-based objective function."""
    events = []
    
    async def event_handler(event: Event):
        events.append(event)
    
    task_queue.add_subscriber(event_handler)
    await task_queue.add_task(task_config)
    
    # Start processing
    process_task = asyncio.create_task(task_queue.start_processing())
    
    # Wait for task to complete
    for _ in range(10):  # Try for up to 1 second
        await asyncio.sleep(0.1)
        tasks = await task_queue.list_tasks()
        if tasks[0]["status"] == "completed":
            break
    
    # Stop processing
    task_queue._stopped = True
    await process_task
    
    # Check events
    status_events = [e for e in events if e.type == EventType.TASK_STATUS_CHANGED]
    assert len(status_events) >= 2  # At least pending -> running -> completed
    assert any(e.data["status"] == "running" for e in status_events)
    assert any(e.data["status"] == "completed" for e in status_events)
    
    # Check final state
    tasks = await task_queue.list_tasks()
    assert len(tasks) == 1
    task = tasks[0]
    assert task["status"] == "completed"
    assert task["result"] is not None
    assert isinstance(task["result"]["best_value"], float)

@pytest.mark.asyncio
async def test_task_control_with_string_objective(task_queue: TaskQueue, task_config: Dict[str, Any]):
    """Test task control operations with string-based objective function."""
    await task_queue.add_task(task_config)
    
    # Start processing
    process_task = asyncio.create_task(task_queue.start_processing())
    await asyncio.sleep(0.1)  # Allow time for processing to start
    
    # Get task ID
    tasks = await task_queue.list_tasks()
    task_id = tasks[0]["task_id"]
    
    # Test pause
    success = await task_queue.pause_task(task_id)
    assert success
    task = await task_queue.get_task(task_id)
    assert task["status"] == "paused"
    
    # Test resume
    success = await task_queue.resume_task(task_id)
    assert success
    task = await task_queue.get_task(task_id)
    assert task["status"] == "running"
    
    # Test stop
    success = await task_queue.stop_task(task_id)
    assert success
    task = await task_queue.get_task(task_id)
    assert task["status"] == "stopped"
    
    # Cleanup
    task_queue._stopped = True
    await process_task

@pytest.mark.asyncio
async def test_multiple_tasks_with_string_objectives(task_queue: TaskQueue, task_config: Dict[str, Any]):
    """Test processing multiple tasks with string-based objective functions."""
    # Create tasks with different objective functions
    tasks = []
    for i in range(3):
        config = task_config.copy()
        config["name"] = f"Task {i}"
        config["objective_fn"] = f"def objective(x):\n    return (x - {i}) ** 2"
        tasks.append(config)
    
    # Add tasks to queue
    for task in tasks:
        await task_queue.add_task(task)
    
    # Start processing
    process_task = asyncio.create_task(task_queue.start_processing())
    await asyncio.sleep(0.1)  # Allow time for first task to start
    
    # Check first task is running
    queue_tasks = await task_queue.list_tasks()
    assert len(queue_tasks) == 3
    assert any(t["status"] == "running" for t in queue_tasks)
    
    # Stop processing
    task_queue._stopped = True
    await process_task 