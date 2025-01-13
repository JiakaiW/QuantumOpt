"""Unified event system for optimization updates."""
import logging
import asyncio
from typing import Dict, Any, Callable, List, Union, Awaitable, Optional
from enum import Enum, auto
from dataclasses import dataclass

logger = logging.getLogger(__name__)

class EventType(Enum):
    """Standard event types across the system."""
    # Queue Events
    QUEUE_STARTED = auto()
    QUEUE_STOPPED = auto()
    QUEUE_PAUSED = auto()
    QUEUE_RESUMED = auto()
    QUEUE_ERROR = auto()
    
    # Task Events
    TASK_ADDED = auto()
    TASK_STARTED = auto()
    TASK_COMPLETED = auto()
    TASK_FAILED = auto()
    TASK_PAUSED = auto()
    TASK_RESUMED = auto()
    TASK_STOPPED = auto()
    TASK_REMOVED = auto()  # Added for task removal events
    TASK_STATUS_CHANGED = auto()  # General status change event
    
    # Optimization Events
    ITERATION_COMPLETED = auto()  # More descriptive than just ITERATION
    NEW_BEST_FOUND = auto()      # More descriptive than just NEW_BEST
    OPTIMIZATION_COMPLETED = auto()  # Consistent naming
    OPTIMIZATION_ERROR = auto()      # Specific optimization errors
    
    # System Events
    ERROR = auto()
    WARNING = auto()
    INFO = auto()

@dataclass
class TaskConfig:
    """Standard task configuration structure."""
    parameter_config: Dict[str, Any]  # bounds, initial values, etc.
    optimizer_config: Dict[str, Any]  # optimizer type, budget, etc.
    execution_config: Dict[str, Any]  # retries, timeout, etc.
    objective_fn: Callable  # The function to optimize

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary format."""
        return {
            "parameter_config": self.parameter_config,
            "optimizer_config": self.optimizer_config,
            "execution_config": self.execution_config,
            # objective_fn is not serializable
        }

@dataclass
class TaskState:
    """Standard task state structure."""
    task_id: str
    status: str  # pending, running, paused, completed, failed, stopped
    config: TaskConfig
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary format."""
        return {
            "task_id": self.task_id,
            "status": self.status,
            "config": self.config.to_dict(),
            "result": self.result,
            "error": self.error
        }

@dataclass
class APIResponse:
    """Standard API response structure."""
    status: str  # "success" or "error"
    data: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert response to dictionary format."""
        return {
            "status": self.status,
            "data": self.data,
            "error": self.error
        }

class Event:
    """Standard event structure."""
    
    def __init__(self, 
                 event_type: EventType,
                 task_id: Optional[str] = None,
                 data: Optional[Dict[str, Any]] = None):
        """Initialize event.
        
        Args:
            event_type: Type of the event
            task_id: Optional ID of the task this event relates to
            data: Additional event data
        """
        self.type = event_type
        self.task_id = task_id
        self.data = data or {}
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary format."""
        return {
            "type": self.type.name,
            "task_id": self.task_id,
            "data": self.data
        }

class EventEmitter:
    """Base class for components that emit events."""
    
    def __init__(self):
        """Initialize event emitter."""
        self._subscribers: List[Callable[[Event], Union[None, Awaitable[None]]]] = []
        
    def add_subscriber(self, callback: Callable[[Event], Union[None, Awaitable[None]]]) -> None:
        """Add a subscriber for events.
        
        Args:
            callback: Function to call when an event occurs
        """
        self._subscribers.append(callback)
        
    async def emit(self, event: Event) -> None:
        """Emit an event to all subscribers.
        
        Args:
            event: Event to emit
        """
        for callback in self._subscribers:
            try:
                result = callback(event)
                if asyncio.iscoroutine(result):
                    await result
            except Exception as e:
                logger.error(f"Error notifying subscriber: {e}")

# Helper functions for creating common events
def create_task_event(event_type: EventType, task_id: str, **data) -> Event:
    """Create a task-related event."""
    return Event(event_type, task_id=task_id, data=data)

def create_optimization_event(event_type: EventType, task_id: str, **data) -> Event:
    """Create an optimization-related event."""
    return Event(event_type, task_id=task_id, data=data)

def create_system_event(event_type: EventType, message: str, **data) -> Event:
    """Create a system-related event."""
    data["message"] = message
    return Event(event_type, data=data)

def create_queue_event(event_type: EventType, **data) -> Event:
    """Create a queue-related event."""
    return Event(event_type, data=data)

def create_api_response(status: str = "success", data: Optional[Dict[str, Any]] = None, 
                       error: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Create a standardized API response."""
    return APIResponse(status=status, data=data, error=error).to_dict() 