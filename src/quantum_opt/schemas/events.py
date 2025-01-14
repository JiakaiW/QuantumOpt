"""Event schema definitions for WebSocket communication."""
from typing import Dict, Any, Optional, Literal
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict

class OptimizationEvent(BaseModel):
    """Base class for optimization events."""
    model_config = ConfigDict(strict=True)
    
    event_type: str = Field(..., description="Type of the event")
    task_id: str = Field(..., description="ID of the task this event relates to")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="When the event occurred")

class IterationCompleted(OptimizationEvent):
    """Event emitted when an optimization iteration completes."""
    event_type: Literal["ITERATION_COMPLETED"] = Field("ITERATION_COMPLETED")
    iteration: int = Field(..., description="Current iteration number")
    value: float = Field(..., description="Current objective value")
    best_value: float = Field(..., description="Best objective value so far")
    parameters: Dict[str, float] = Field(..., description="Current parameter values")
