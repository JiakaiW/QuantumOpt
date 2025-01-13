"""API schemas for quantum optimization."""
from typing import Dict, Any, Optional, List, Callable, Union, Literal
from pydantic import BaseModel, Field, validator

class ParameterConfig(BaseModel):
    """Configuration for a single parameter."""
    lower_bound: float = Field(..., description="Lower bound for the parameter")
    upper_bound: float = Field(..., description="Upper bound for the parameter")
    init: Optional[float] = Field(None, description="Initial value for the parameter")
    scale: Literal["linear", "log"] = Field("linear", description="Scale type for the parameter")
    
    @validator("init", pre=True, always=True)
    def set_default_init(cls, v, values):
        """Set default initial value to middle of bounds if not provided."""
        if v is None and "lower_bound" in values and "upper_bound" in values:
            return (values["lower_bound"] + values["upper_bound"]) / 2
        return v
    
    @validator("upper_bound")
    def upper_bound_must_be_greater(cls, v, values):
        """Validate that upper bound is greater than lower bound."""
        if "lower_bound" in values and v <= values["lower_bound"]:
            raise ValueError("upper_bound must be greater than lower_bound")
        return v

class OptimizerConfig(BaseModel):
    """Configuration for the optimizer."""
    optimizer_type: Literal["CMA", "OnePlusOne"] = Field("CMA", description="Type of optimizer to use")
    budget: int = Field(..., description="Number of function evaluations allowed")
    num_workers: int = Field(1, ge=1, description="Number of parallel workers")
    
    @validator("budget")
    def budget_must_be_positive(cls, v):
        """Validate that budget is positive."""
        if v <= 0:
            raise ValueError("budget must be positive")
        return v

class ExecutionConfig(BaseModel):
    """Configuration for execution parameters."""
    max_retries: int = Field(default=3, description="Maximum number of retries for failed evaluations")
    timeout: float = Field(default=3600.0, description="Timeout in seconds for the optimization")

class OptimizationConfig(BaseModel):
    """Configuration for an optimization task."""
    name: str = Field(..., description="Name of the optimization task")
    parameter_config: Dict[str, ParameterConfig] = Field(..., description="Parameter configurations")
    optimizer_config: OptimizerConfig = Field(..., description="Optimizer configuration")
    execution_config: ExecutionConfig = Field(default_factory=ExecutionConfig, description="Execution configuration")
    objective_fn: Callable[..., float] = Field(..., description="Objective function to optimize")

class TaskResponse(BaseModel):
    """Response model for task creation."""
    task_id: str = Field(..., description="Unique identifier for the created task")
    status: str = Field(..., description="Initial status of the task")

class TaskState(BaseModel):
    """Model representing the state of a task."""
    task_id: str = Field(..., description="Unique identifier for the task")
    status: str = Field(..., description="Current status of the task")
    config: OptimizationConfig = Field(..., description="Task configuration")
    result: Optional[Dict[str, Any]] = Field(None, description="Optimization results if completed")
    error: Optional[str] = Field(None, description="Error message if failed")
    
    @validator("status")
    def status_must_be_valid(cls, v):
        """Validate that status is one of the allowed values."""
        allowed = {"pending", "running", "paused", "completed", "failed", "stopped"}
        if v not in allowed:
            raise ValueError(f"status must be one of {allowed}")
        return v

class WebSocketMessage(BaseModel):
    """Format for WebSocket messages."""
    type: str = Field(..., description="Type of the message (event, command, response)")
    data: Dict[str, Any] = Field(..., description="Message payload")

class APIResponse(BaseModel):
    """Standard API response format."""
    status: str = Field(..., description="Response status (success or error)")
    data: Optional[Dict[str, Any]] = Field(None, description="Response data if successful")
    error: Optional[Dict[str, Any]] = Field(None, description="Error details if unsuccessful")
    
    @validator("status")
    def status_must_be_valid(cls, v):
        """Validate that status is either success or error."""
        if v not in {"success", "error"}:
            raise ValueError("status must be either 'success' or 'error'")
        return v 