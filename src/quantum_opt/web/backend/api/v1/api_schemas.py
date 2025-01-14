"""API schemas for quantum optimization."""
from typing import Dict, Any, Optional, List, Literal
from pydantic import BaseModel, Field, ConfigDict, field_validator

class ParameterConfig(BaseModel):
    """Configuration for an optimization parameter."""
    model_config = ConfigDict(strict=True)
    
    lower_bound: float = Field(..., description="Lower bound for the parameter")
    upper_bound: float = Field(..., description="Upper bound for the parameter")
    init: Optional[float] = Field(None, description="Initial value for the parameter")
    scale: Literal["linear", "log"] = Field("linear", description="Scale type for the parameter")

class OptimizerConfig(BaseModel):
    """Configuration for the optimizer."""
    model_config = ConfigDict(strict=True)
    
    optimizer_type: Literal["OnePlusOne", "CMA"] = Field(..., description="Type of optimizer to use")
    budget: int = Field(..., ge=1, description="Number of function evaluations allowed")
    num_workers: int = Field(1, ge=1, description="Number of parallel workers")

class ExecutionConfig(BaseModel):
    """Configuration for task execution."""
    model_config = ConfigDict(strict=True)
    
    max_retries: int = Field(3, ge=0, description="Maximum number of retries for failed evaluations")
    timeout: float = Field(3600.0, gt=0, description="Timeout in seconds for the optimization")

class OptimizationConfig(BaseModel):
    """Configuration for an optimization task."""
    model_config = ConfigDict(strict=True)
    
    name: str = Field(..., min_length=1, description="Name of the optimization task")
    parameter_config: Dict[str, ParameterConfig] = Field(
        ..., 
        description="Parameter configurations"
    )
    optimizer_config: OptimizerConfig = Field(..., description="Optimizer configuration")
    execution_config: ExecutionConfig = Field(
        default_factory=ExecutionConfig,
        description="Execution configuration"
    )
    objective_fn: str = Field(
        ..., 
        min_length=1,
        description="String representation of the objective function to optimize"
    )

    @field_validator("parameter_config")
    def validate_parameter_config(cls, v: Dict[str, ParameterConfig]) -> Dict[str, ParameterConfig]:
        """Validate parameter configuration."""
        if not v:
            raise ValueError("At least one parameter must be defined")
        for name, config in v.items():
            if config.lower_bound >= config.upper_bound:
                raise ValueError(f"Parameter {name}: lower_bound must be less than upper_bound")
            if config.init is not None:
                if config.init < config.lower_bound or config.init > config.upper_bound:
                    raise ValueError(
                        f"Parameter {name}: init value must be between lower_bound and upper_bound"
                    )
        return v

class APIResponse(BaseModel):
    """Standard API response format."""
    model_config = ConfigDict(strict=True)
    
    status: Literal["success", "error"] = Field(..., description="Response status")
    data: Optional[Dict[str, Any]] = Field(None, description="Response data")
    error: Optional[Dict[str, str]] = Field(None, description="Error details")

    @field_validator("error")
    def validate_error(cls, v: Optional[Dict[str, str]], info) -> Optional[Dict[str, str]]:
        """Validate that error is present only for error status."""
        if info.data["status"] == "error" and not v:
            raise ValueError("error must be provided when status is 'error'")
        if info.data["status"] == "success" and v:
            raise ValueError("error should not be provided when status is 'success'")
        return v

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