"""Event system for optimization."""
from typing import Any, Callable, Dict, List, Optional
import asyncio
from dataclasses import dataclass

@dataclass
class OptimizationEvent:
    """Event data for optimization events."""
    name: str
    data: Dict[str, Any]

class OptimizationEventSystem:
    """Event system for optimization."""
    
    def __init__(self):
        """Initialize event system."""
        self._handlers: Dict[str, List[Callable]] = {}
        self._paused = False
        self._stopped = False
        self._state = {}
    
    def on(self, event_name: str):
        """Decorator to register event handlers."""
        def decorator(handler: Callable):
            if event_name not in self._handlers:
                self._handlers[event_name] = []
            self._handlers[event_name].append(handler)
            return handler
        return decorator

    def subscribe(self, event_name: str, handler: Callable):
        """Subscribe to an event."""
        if event_name not in self._handlers:
            self._handlers[event_name] = []
        self._handlers[event_name].append(handler)
    
    async def emit(self, event: OptimizationEvent):
        """Emit an event to all handlers."""
        if self._paused or self._stopped:
            return
            
        if event.name in self._handlers:
            for handler in self._handlers[event.name]:
                if asyncio.iscoroutinefunction(handler):
                    await handler(event)
                else:
                    handler(event)
    
    def update_state(self, **kwargs):
        """Update event system state."""
        self._state.update(kwargs)
    
    def pause(self):
        """Pause event emission."""
        self._paused = True
    
    def resume(self):
        """Resume event emission."""
        self._paused = False
    
    def stop(self):
        """Stop event emission."""
        self._stopped = True
    
    @property
    def state(self) -> Dict[str, Any]:
        """Get current state."""
        return self._state.copy() 