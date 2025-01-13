"""Tests for the event system."""
import pytest
from typing import Dict, Any, List
from quantum_opt.utils.events import (
    Event,
    EventType,
    EventEmitter,
    TaskConfig,
    TaskState,
    APIResponse,
    create_task_event,
    create_optimization_event,
    create_system_event,
    create_queue_event,
    create_api_response
)

def test_event_type_values():
    """Test that all expected event types are defined."""
    # Queue events
    assert hasattr(EventType, "QUEUE_STARTED")
    assert hasattr(EventType, "QUEUE_STOPPED")
    assert hasattr(EventType, "QUEUE_PAUSED")
    assert hasattr(EventType, "QUEUE_RESUMED")
    assert hasattr(EventType, "QUEUE_ERROR")
    
    # Task events
    assert hasattr(EventType, "TASK_ADDED")
    assert hasattr(EventType, "TASK_STARTED")
    assert hasattr(EventType, "TASK_COMPLETED")
    assert hasattr(EventType, "TASK_FAILED")
    assert hasattr(EventType, "TASK_PAUSED")
    assert hasattr(EventType, "TASK_RESUMED")
    assert hasattr(EventType, "TASK_STOPPED")
    assert hasattr(EventType, "TASK_STATUS_CHANGED")
    
    # Optimization events
    assert hasattr(EventType, "ITERATION_COMPLETED")
    assert hasattr(EventType, "NEW_BEST_FOUND")
    assert hasattr(EventType, "OPTIMIZATION_COMPLETED")
    assert hasattr(EventType, "OPTIMIZATION_ERROR")
    
    # System events
    assert hasattr(EventType, "ERROR")
    assert hasattr(EventType, "WARNING")
    assert hasattr(EventType, "INFO")

def test_task_config():
    """Test TaskConfig creation and serialization."""
    def dummy_objective(x: float) -> float:
        return x * x
    
    config = TaskConfig(
        parameter_config={"x": {"min": 0, "max": 1}},
        optimizer_config={"type": "nevergrad", "budget": 100},
        execution_config={"max_retries": 3},
        objective_fn=dummy_objective
    )
    
    # Test to_dict method
    config_dict = config.to_dict()
    assert "parameter_config" in config_dict
    assert "optimizer_config" in config_dict
    assert "execution_config" in config_dict
    assert "objective_fn" not in config_dict  # Should not be serialized

def test_task_state():
    """Test TaskState creation and serialization."""
    def dummy_objective(x: float) -> float:
        return x * x
    
    config = TaskConfig(
        parameter_config={"x": {"min": 0, "max": 1}},
        optimizer_config={"type": "nevergrad", "budget": 100},
        execution_config={"max_retries": 3},
        objective_fn=dummy_objective
    )
    
    state = TaskState(
        task_id="test-task",
        status="running",
        config=config,
        result={"best_value": 0.1},
        error=None
    )
    
    # Test to_dict method
    state_dict = state.to_dict()
    assert state_dict["task_id"] == "test-task"
    assert state_dict["status"] == "running"
    assert "config" in state_dict
    assert state_dict["result"] == {"best_value": 0.1}
    assert state_dict["error"] is None

def test_api_response():
    """Test APIResponse creation and serialization."""
    response = APIResponse(
        status="success",
        data={"result": "ok"},
        error=None
    )
    
    # Test to_dict method
    response_dict = response.to_dict()
    assert response_dict["status"] == "success"
    assert response_dict["data"] == {"result": "ok"}
    assert response_dict["error"] is None

def test_event_creation():
    """Test Event creation and properties."""
    event = Event(
        event_type=EventType.TASK_STARTED,
        task_id="test-task",
        data={"status": "running"}
    )
    
    assert event.type == EventType.TASK_STARTED
    assert event.task_id == "test-task"
    assert event.data == {"status": "running"}
    
    # Test to_dict method
    event_dict = event.to_dict()
    assert event_dict["type"] == EventType.TASK_STARTED.name
    assert event_dict["task_id"] == "test-task"
    assert event_dict["data"] == {"status": "running"}

@pytest.mark.asyncio
async def test_event_emitter():
    """Test EventEmitter subscription and emission."""
    emitter = EventEmitter()
    events: List[Event] = []
    
    # Test synchronous subscriber
    def sync_handler(event: Event) -> None:
        events.append(event)
    
    # Test async subscriber
    async def async_handler(event: Event) -> None:
        events.append(event)
    
    # Add subscribers
    emitter.add_subscriber(sync_handler)
    emitter.add_subscriber(async_handler)
    
    # Create and emit test event
    test_event = Event(
        event_type=EventType.TASK_STARTED,
        task_id="test-task",
        data={"status": "running"}
    )
    
    await emitter.emit(test_event)
    
    # Both handlers should have received the event
    assert len(events) == 2
    assert all(e.type == EventType.TASK_STARTED for e in events)
    assert all(e.task_id == "test-task" for e in events)

def test_event_creation_helpers():
    """Test event creation helper functions."""
    # Test task event creation
    task_event = create_task_event(
        event_type=EventType.TASK_STARTED,
        task_id="test-task",
        status="running"
    )
    assert task_event.type == EventType.TASK_STARTED
    assert task_event.task_id == "test-task"
    assert task_event.data["status"] == "running"
    
    # Test optimization event creation
    opt_event = create_optimization_event(
        event_type=EventType.ITERATION_COMPLETED,
        task_id="test-task",
        iteration=10,
        value=0.5
    )
    assert opt_event.type == EventType.ITERATION_COMPLETED
    assert opt_event.task_id == "test-task"
    assert opt_event.data["iteration"] == 10
    assert opt_event.data["value"] == 0.5
    
    # Test system event creation
    sys_event = create_system_event(
        event_type=EventType.ERROR,
        message="Test error",
        code=500
    )
    assert sys_event.type == EventType.ERROR
    assert sys_event.data["message"] == "Test error"
    assert sys_event.data["code"] == 500
    
    # Test queue event creation
    queue_event = create_queue_event(
        event_type=EventType.QUEUE_STARTED,
        task_count=5
    )
    assert queue_event.type == EventType.QUEUE_STARTED
    assert queue_event.data["task_count"] == 5

def test_api_response_helper():
    """Test API response creation helper function."""
    # Test success response
    success_response = create_api_response(
        status="success",
        data={"result": "ok"}
    )
    assert success_response["status"] == "success"
    assert success_response["data"] == {"result": "ok"}
    assert success_response["error"] is None
    
    # Test error response
    error_response = create_api_response(
        status="error",
        error={"message": "Test error"}
    )
    assert error_response["status"] == "error"
    assert error_response["data"] is None
    assert error_response["error"] == {"message": "Test error"} 