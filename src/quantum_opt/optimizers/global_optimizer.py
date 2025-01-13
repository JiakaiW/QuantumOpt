"""Global optimization using nevergrad."""
import logging
from typing import Dict, Any, Optional

import nevergrad as ng

from .base_optimizer import BaseParallelOptimizer
from .optimization_schemas import OptimizationConfig

logger = logging.getLogger(__name__)

class MultiprocessingGlobalOptimizer(BaseParallelOptimizer):
    """Global optimizer using nevergrad with multiprocessing."""
    
    def __init__(self, config: OptimizationConfig, task_id: Optional[str] = None):
        """Initialize global optimizer.
        
        Args:
            config: Optimizer configuration containing parameter bounds, optimizer settings,
                   and objective function
            task_id: Optional task ID for event tracking
        """
        super().__init__(config, task_id)
        
    def _create_optimizer(self) -> ng.optimizers.base.Optimizer:
        """Create and return a nevergrad optimizer instance."""
        # Create parameter space
        param_space = {}
        for name, param_config in self.config.parameter_config.items():
            # Create parameter based on scale
            if param_config.scale == "log":
                # Ensure positive bounds for log scale
                lower = max(1e-10, param_config.lower_bound)
                upper = max(lower * 1.1, param_config.upper_bound)
                init = max(lower, min(upper, param_config.init or (lower * upper) ** 0.5))
                
                param_space[name] = ng.p.Log(
                    init=init,
                    lower=lower,
                    upper=upper
                )
            else:
                param_space[name] = ng.p.Scalar(
                    init=param_config.init,
                    lower=param_config.lower_bound,
                    upper=param_config.upper_bound
                )
            
        # Create instrumentation
        instrumentation = ng.p.Instrumentation(**param_space)
        
        # Create optimizer based on type
        if self.config.optimizer_config.optimizer_type == "CMA":
            return ng.optimizers.CMA(
                parametrization=instrumentation,
                budget=self.config.optimizer_config.budget,
                num_workers=self.config.optimizer_config.num_workers
            )
        else:  # OnePlusOne
            return ng.optimizers.OnePlusOne(
                parametrization=instrumentation,
                budget=self.config.optimizer_config.budget,
                num_workers=self.config.optimizer_config.num_workers
            )
        
    async def _evaluate_candidate(self, candidate: Dict[str, Any]) -> float:
        """Evaluate a candidate solution.
        
        Args:
            candidate: Dictionary of parameter values to evaluate
            
        Returns:
            float: The objective function value
            
        Raises:
            Exception: If evaluation fails, the original error is propagated
        """
        try:
            # Call objective function with unpacked parameters
            result = self.config.objective_fn(**candidate)
            return float(result)
        except Exception as e:
            logger.error(f"Error evaluating candidate: {str(e)}")
            # Re-raise the original exception to preserve the error message
            raise e from None 