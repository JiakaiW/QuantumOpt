"""API schemas for quantum optimization."""
from typing import Dict, Any, Optional, List, Union, Literal
from pydantic import BaseModel, Field, field_validator, ConfigDict, ValidationInfo

class ParameterConfig(BaseModel):
    """Configuration for a single parameter."""
    model_config = ConfigDict(strict=True)
    
    lower_bound: float = Field(..., description="Lower bound for the parameter")
    upper_bound: float = Field(..., description="Upper bound for the parameter")
    init: Optional[float] = Field(None, description="Initial value for the parameter")
    scale: Literal["linear", "log"] = Field("linear", description="Scale type for the parameter")
    
    @field_validator("init", mode="before")
    def set_default_init(cls, v: Optional[float], info: ValidationInfo) -> float:
        """Set default initial value to middle of bounds if not provided."""
        if v is not None:
            return v
        if "lower_bound" in info.data and "upper_bound" in info.data:
            return (info.data["lower_bound"] + info.data["upper_bound"]) / 2
        return 0.0
    
    @field_validator("upper_bound")
    def upper_bound_must_be_greater(cls, v: float, info: ValidationInfo) -> float:
        """Validate that upper bound is greater than lower bound."""
        if "lower_bound" in info.data and v <= info.data["lower_bound"]:
            raise ValueError("upper_bound must be greater than lower_bound")
        return v

class OptimizerConfig(BaseModel):
    """Configuration for the optimizer."""
    model_config = ConfigDict(strict=True)
    
    optimizer_type: Literal["CMA", "OnePlusOne"] = Field("CMA", description="Type of optimizer to use")
    budget: int = Field(..., description="Number of function evaluations allowed")
    num_workers: int = Field(1, ge=1, description="Number of parallel workers")
    
    @field_validator("budget")
    def budget_must_be_positive(cls, v) -> int:
        """Validate that budget is positive."""
        if v <= 0:
            raise ValueError("budget must be positive")
        return v

class ExecutionConfig(BaseModel):
    """Configuration for execution parameters."""
    model_config = ConfigDict(strict=True)
    
    max_retries: int = Field(default=3, description="Maximum number of retries for failed evaluations")
    timeout: float = Field(default=3600.0, description="Timeout in seconds for the optimization")

class OptimizationConfig(BaseModel):
    """Configuration for an optimization task."""
    model_config = ConfigDict(strict=True)
    
    name: str = Field(..., description="Name of the optimization task")
    parameter_config: Dict[str, ParameterConfig] = Field(..., description="Parameter configurations")
    optimizer_config: OptimizerConfig = Field(..., description="Optimizer configuration")
    execution_config: ExecutionConfig = Field(default_factory=ExecutionConfig, description="Execution configuration")
    objective_fn: str = Field(
        ..., 
        description="String representation of the objective function to optimize. "
        "Must be a valid Python function definition that takes parameters matching "
        "the parameter_config keys and returns a float value. "
        "Example: 'def objective(x, y): return x**2 + y**2'"
    )

class TaskResponse(BaseModel):
    """Response model for task creation."""
    model_config = ConfigDict(strict=True)
    
    task_id: str = Field(..., description="Unique identifier for the created task")
    status: str = Field(..., description="Initial status of the task")

class TaskState(BaseModel):
    """Model representing the state of a task."""
    model_config = ConfigDict(strict=True)
    
    task_id: str = Field(..., description="Unique identifier for the task")
    status: str = Field(..., description="Current status of the task")
    config: OptimizationConfig = Field(..., description="Task configuration")
    result: Optional[Dict[str, Any]] = Field(None, description="Optimization results if completed")
    error: Optional[str] = Field(None, description="Error message if failed")
    
    @field_validator("status")
    def status_must_be_valid(cls, v) -> str:
        """Validate that status is one of the allowed values."""
        allowed = {"pending", "running", "paused", "completed", "failed", "stopped"}
        if v not in allowed:
            raise ValueError(f"status must be one of {allowed}")
        return v

class WebSocketMessage(BaseModel):
    """Format for WebSocket messages."""
    model_config = ConfigDict(strict=True)
    
    type: str = Field(..., description="Type of the message (event, command, response)")
    data: Dict[str, Any] = Field(..., description="Message payload")

class APIResponse(BaseModel):
    """Standard API response format."""
    model_config = ConfigDict(strict=True)
    
    status: str = Field(..., description="Response status (success or error)")
    data: Optional[Dict[str, Any]] = Field(None, description="Response data if successful")
    error: Optional[Dict[str, Any]] = Field(None, description="Error details if unsuccessful")
    
    @field_validator("status")
    def status_must_be_valid(cls, v) -> str:
        """Validate that status is either success or error."""
        if v not in {"success", "error"}:
            raise ValueError("status must be either 'success' or 'error'")
        return v