"""Event system for optimization."""
from typing import Any, Dict, List, Optional, Callable, Awaitable, Union
import asyncio

class OptimizationEvent:
    """Event types for optimization."""
    ITERATION_COMPLETE = "iteration_complete"
    OPTIMIZATION_COMPLETE = "optimization_complete"
    ERROR = "error"

class OptimizationEventSystem:
    """Event system for optimization."""
    def __init__(self):
        """Initialize event system."""
        self._handlers = {
            OptimizationEvent.ITERATION_COMPLETE: [],
            OptimizationEvent.OPTIMIZATION_COMPLETE: [],
            OptimizationEvent.ERROR: []
        }
        self._state = {}
        self._is_paused = False
        self._is_stopped = False

    def subscribe(self, event_name: str, handler: Union[Callable, Awaitable]):
        """Subscribe to an event."""
        if event_name not in self._handlers:
            self._handlers[event_name] = []
        self._handlers[event_name].append(handler)

    async def emit(self, event_name: str, **data):
        """Emit an event."""
        if event_name not in self._handlers:
            return
        
        for handler in self._handlers[event_name]:
            if asyncio.iscoroutinefunction(handler):
                await handler(data)
            else:
                handler(data)

    def update_state(self, **kwargs):
        """Update event system state."""
        self._state.update(kwargs)

    def get_state(self, key: str) -> Optional[Any]:
        """Get value from state."""
        return self._state.get(key)

    def pause(self):
        """Pause optimization."""
        self._is_paused = True

    def resume(self):
        """Resume optimization."""
        self._is_paused = False

    def stop(self):
        """Stop optimization."""
        self._is_stopped = True

    def is_paused(self) -> bool:
        """Check if optimization is paused."""
        return self._is_paused

    def is_stopped(self) -> bool:
        """Check if optimization is stopped."""
        return self._is_stopped 