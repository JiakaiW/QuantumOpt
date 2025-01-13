"""Schemas for optimizer configuration."""
from typing import Dict, Any, Optional, Callable, Union, Literal, Self
import inspect
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict

class ParameterConfig(BaseModel):
    """Configuration for a single parameter."""
    model_config = ConfigDict(strict=True)
    
    lower_bound: float = Field(..., description="Lower bound for the parameter")
    upper_bound: float = Field(..., description="Upper bound for the parameter")
    init: Optional[float] = Field(None, description="Initial value for the parameter")
    scale: Literal["linear", "log"] = Field("linear", description="Scale type for the parameter")
    
    @field_validator("init", mode="before")
    def set_default_init(cls, v: Optional[float], info) -> float:
        """Set default initial value based on bounds."""
        if v is not None:
            return v
            
        data = info.data
        lower = data.get("lower_bound", 0.0)
        upper = data.get("upper_bound", 0.0)
        scale = data.get("scale", "linear")
        
        if scale == "log":
            return max(1e-10, lower)
        return (lower + upper) / 2

    @field_validator("upper_bound")
    def upper_bound_must_be_greater(cls, v: float, info) -> float:
        """Validate that upper bound is greater than lower bound."""
        lower_bound = info.data.get("lower_bound")
        if lower_bound is not None and v <= lower_bound:
            raise ValueError("upper_bound must be greater than lower_bound")
        return v

class OptimizerConfig(BaseModel):
    """Configuration for the optimizer."""
    model_config = ConfigDict(strict=True)
    
    optimizer_type: Literal["OnePlusOne", "CMA"] = Field("OnePlusOne", description="Type of optimizer to use")
    budget: int = Field(100, description="Maximum number of function evaluations")
    num_workers: int = Field(1, description="Number of parallel workers")
    
    @field_validator("budget")
    def budget_must_be_positive(cls, v: int) -> int:
        """Validate that budget is positive."""
        if v <= 0:
            raise ValueError("budget must be positive")
        return v

class OptimizationConfig(BaseModel):
    """Complete configuration for optimization."""
    model_config = ConfigDict(strict=True)
    
    name: str = Field(..., description="Name of the optimization task")
    parameter_config: Dict[str, ParameterConfig] = Field(..., description="Parameter configurations")
    optimizer_config: OptimizerConfig = Field(
        default_factory=lambda: OptimizerConfig(
            optimizer_type="CMA",
            budget=100,
            num_workers=1
        ),
        description="Optimizer settings"
    )
    objective_fn: Union[Callable[..., float], str] = Field(
        ..., 
        description="Objective function to minimize. Can be a callable or a string containing Python function definition"
    )
    objective_fn_source: Optional[str] = Field(
        None,
        description="Source code of the objective function for display. Auto-populated from callable if not provided."
    )
    
    @model_validator(mode='after')
    def extract_source_code(self) -> Self:
        """Extract source code from callable objective function if needed."""
        if callable(self.objective_fn) and not self.objective_fn_source:
            try:
                self.objective_fn_source = inspect.getsource(self.objective_fn)
            except (TypeError, OSError):
                self.objective_fn_source = f"def objective{inspect.signature(self.objective_fn)}:\n    # Source code not available\n    ..."
        elif isinstance(self.objective_fn, str) and not self.objective_fn_source:
            self.objective_fn_source = self.objective_fn
            
        return self
    
    def model_dump(self, *args, **kwargs) -> Dict[str, Any]:
        """Override model_dump to handle callable serialization."""
        data = super().model_dump(*args, **kwargs)
        if callable(data.get('objective_fn')):
            data['objective_fn'] = self.objective_fn_source
        return data