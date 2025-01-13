"""Schemas for optimizer configuration."""
from typing import Dict, Any, Optional, Callable, Union, Literal
from pydantic import BaseModel, Field, field_validator

class ParameterConfig(BaseModel):
    """Configuration for a single parameter."""
    lower_bound: float = Field(..., description="Lower bound for the parameter")
    upper_bound: float = Field(..., description="Upper bound for the parameter")
    init: Optional[float] = Field(None, description="Initial value for the parameter")
    scale: Literal["linear", "log"] = Field("linear", description="Scale type for the parameter")
    
    @field_validator("init", mode="before")
    @classmethod
    def set_default_init(cls, v: Optional[float], info) -> float:
        """Set default initial value based on bounds."""
        if v is not None:
            return v
            
        values = info.data
        lower = values.get("lower_bound", 0.0)
        upper = values.get("upper_bound", 0.0)
        scale = values.get("scale", "linear")
        
        if scale == "log":
            return max(1e-10, lower)
        return (lower + upper) / 2

class OptimizerConfig(BaseModel):
    """Configuration for the optimizer."""
    optimizer_type: Literal["OnePlusOne", "CMA"] = Field("OnePlusOne", description="Type of optimizer to use")
    budget: int = Field(100, description="Maximum number of function evaluations")
    num_workers: int = Field(1, description="Number of parallel workers")

class OptimizationConfig(BaseModel):
    """Complete configuration for optimization."""
    name: str = Field(..., description="Name of the optimization task")
    parameter_config: Dict[str, ParameterConfig] = Field(..., description="Parameter configurations")
    optimizer_config: OptimizerConfig = Field(default_factory=lambda: OptimizerConfig(), description="Optimizer settings")
    objective_fn: Callable[..., float] = Field(..., description="Objective function to minimize") 