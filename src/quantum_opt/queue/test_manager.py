"""Tests for the task queue manager."""
import pytest
import asyncio
from typing import Dict, Any
from unittest.mock import Mock, AsyncMock
from .manager import TaskQueue
from .task import OptimizationTask
from ..utils.events import Event, EventType, create_optimization_event

@pytest.fixture
def task_config() -> Dict[str, Any]:
    """Create a test task configuration."""
    return {
        "parameter_config": {
            "lower_bound": 0,
            "upper_bound": 1
        },
        "optimizer_config": {
            "optimizer_type": "global",
            "budget": 100
        },
        "execution_config": {
            "max_retries": 3,
            "timeout": 300
        },
        "objective_fn": lambda x: x  # Simple test function
    }

@pytest.fixture
def mock_task(task_config) -> Mock:
    """Create a mock task."""
    task = Mock(spec=OptimizationTask)
    task.task_id = "test_task"
    task.status = "pending"
    task.config = task_config
    task.to_dict.return_value = {
        "task_id": task.task_id,
        "status": task.status,
        "config": task_config
    }
    task.add_subscriber = AsyncMock()
    task.pause = AsyncMock(return_value=True)
    task.resume = AsyncMock(return_value=True)
    task.stop = AsyncMock(return_value=True)
    task.start_optimization = AsyncMock()
    return task

@pytest.fixture
def queue() -> TaskQueue:
    """Create a task queue instance."""
    return TaskQueue()

@pytest.mark.asyncio
async def test_add_task(queue: TaskQueue, mock_task: Mock):
    """Test adding a task to the queue."""
    # Setup event capture
    events = []
    queue.add_subscriber(lambda e: events.append(e))
    
    # Add task
    await queue.add_task(mock_task)
    
    # Verify task was added
    assert mock_task.task_id in queue._tasks
    assert len(events) == 1
    assert events[0].type == EventType.TASK_ADDED
    assert events[0].data["task_id"] == mock_task.task_id
    
    # Verify task subscription
    mock_task.add_subscriber.assert_called_once()

@pytest.mark.asyncio
async def test_add_task_no_id(queue: TaskQueue):
    """Test adding a task without an ID."""
    mock_task = Mock(spec=OptimizationTask)
    mock_task.task_id = None
    
    with pytest.raises(ValueError):
        await queue.add_task(mock_task)

@pytest.mark.asyncio
async def test_get_task(queue: TaskQueue, mock_task: Mock):
    """Test retrieving a task by ID."""
    await queue.add_task(mock_task)
    
    # Get existing task
    task = queue.get_task(mock_task.task_id)
    assert task == mock_task
    
    # Get non-existent task
    task = queue.get_task("nonexistent")
    assert task is None

@pytest.mark.asyncio
async def test_list_tasks(queue: TaskQueue, mock_task: Mock):
    """Test listing all tasks."""
    await queue.add_task(mock_task)
    
    tasks = await queue.list_tasks()
    assert len(tasks) == 1
    assert tasks[0] == mock_task.to_dict()

@pytest.mark.asyncio
async def test_pause_task(queue: TaskQueue, mock_task: Mock):
    """Test pausing a task."""
    await queue.add_task(mock_task)
    
    # Pause existing task
    success = await queue.pause_task(mock_task.task_id)
    assert success
    mock_task.pause.assert_called_once()
    
    # Pause non-existent task
    success = await queue.pause_task("nonexistent")
    assert not success

@pytest.mark.asyncio
async def test_resume_task(queue: TaskQueue, mock_task: Mock):
    """Test resuming a task."""
    await queue.add_task(mock_task)
    
    # Resume existing task
    success = await queue.resume_task(mock_task.task_id)
    assert success
    mock_task.resume.assert_called_once()
    
    # Resume non-existent task
    success = await queue.resume_task("nonexistent")
    assert not success

@pytest.mark.asyncio
async def test_stop_task(queue: TaskQueue, mock_task: Mock):
    """Test stopping a task."""
    await queue.add_task(mock_task)
    queue._current_task = mock_task.task_id
    
    # Stop existing task
    success = await queue.stop_task(mock_task.task_id)
    assert success
    mock_task.stop.assert_called_once()
    assert queue._current_task is None
    
    # Stop non-existent task
    success = await queue.stop_task("nonexistent")
    assert not success

@pytest.mark.asyncio
async def test_sequential_processing(queue: TaskQueue, mock_task: Mock):
    """Test sequential processing of tasks."""
    # Setup event capture
    events = []
    queue.add_subscriber(lambda e: events.append(e))
    
    # Add task and start processing
    await queue.add_task(mock_task)
    process_task = asyncio.create_task(queue.start_processing())
    
    # Wait for processing to start
    await asyncio.sleep(0.1)
    
    # Verify task started
    assert queue._current_task == mock_task.task_id
    assert any(e.type == EventType.TASK_STARTED for e in events)
    
    # Simulate task completion
    mock_task.status = "completed"
    await queue._handle_task_event(create_optimization_event(
        EventType.TASK_STATUS_CHANGED,
        task_id=mock_task.task_id,
        status="completed"
    ))
    
    # Verify task completion
    assert queue._current_task is None
    
    # Stop processing
    queue._stopped = True
    await process_task
    
    # Verify queue stopped event
    assert events[-1].type == EventType.QUEUE_STOPPED

@pytest.mark.asyncio
async def test_error_handling(queue: TaskQueue, mock_task: Mock):
    """Test error handling during task processing."""
    # Setup error in task
    mock_task.start_optimization.side_effect = ValueError("Test error")
    
    # Setup event capture
    events = []
    queue.add_subscriber(lambda e: events.append(e))
    
    # Add task and start processing
    await queue.add_task(mock_task)
    process_task = asyncio.create_task(queue.start_processing())
    
    # Wait for processing to start
    await asyncio.sleep(0.1)
    
    # Verify error handling
    error_events = [e for e in events if e.type == EventType.QUEUE_ERROR]
    assert len(error_events) == 0  # Queue shouldn't emit error for task failure
    
    # Stop processing
    queue._stopped = True
    await process_task
    
    # Verify queue stopped
    assert events[-1].type == EventType.QUEUE_STOPPED

@pytest.mark.asyncio
async def test_task_event_forwarding(queue: TaskQueue, mock_task: Mock):
    """Test that task events are forwarded to queue subscribers."""
    # Setup event capture
    events = []
    queue.add_subscriber(lambda e: events.append(e))
    
    # Add task
    await queue.add_task(mock_task)
    
    # Simulate task event
    test_event = create_optimization_event(
        EventType.TASK_STATUS_CHANGED,
        task_id=mock_task.task_id,
        status="running"
    )
    await queue._handle_task_event(test_event)
    
    # Verify event was forwarded
    assert any(e.type == EventType.TASK_STATUS_CHANGED for e in events)
    assert any(e.data["task_id"] == mock_task.task_id for e in events) 