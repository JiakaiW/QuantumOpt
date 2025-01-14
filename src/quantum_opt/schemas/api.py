"""API schema definitions."""
from typing import Dict, Any, Optional, List, Literal
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, field_validator

from .core import OptimizationConfig

class TaskState(BaseModel):
    """Model representing the state of a task."""
    model_config = ConfigDict(strict=True)
    
    task_id: str = Field(..., description="Unique identifier for the task")
    status: Literal["pending", "running", "paused", "completed", "failed", "stopped"] = Field(
        ..., 
        description="Current status of the task"
    )
    config: OptimizationConfig = Field(..., description="Task configuration")
    result: Optional[Dict[str, Any]] = Field(None, description="Optimization results if completed")
    error: Optional[str] = Field(None, description="Error message if failed")

class APIResponse(BaseModel):
    """Standard API response format."""
    model_config = ConfigDict(strict=True)
    
    status: Literal["success", "error"] = Field(..., description="Response status")
    data: Optional[Dict[str, Any]] = Field(None, description="Response data")
    error: Optional[Dict[str, str]] = Field(None, description="Error details")

    @field_validator("error")
    def validate_error(cls, v: Optional[Dict[str, str]], info) -> Optional[Dict[str, str]]:
        """Validate that error is present only for error status."""
        status = info.data.get("status")
        if status == "error" and not v:
            raise ValueError("error must be provided when status is 'error'")
        if status == "success" and v:
            raise ValueError("error should not be provided when status is 'success'")
        return v

class WebSocketMessage(BaseModel):
    """Format for WebSocket messages."""
    model_config = ConfigDict(strict=True)
    
    type: str = Field(..., description="Type of the message")
    data: Dict[str, Any] = Field(..., description="Message payload")
