"""Global optimization using nevergrad."""
import logging
from typing import Dict, Any, Optional
import asyncio

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
        self._paused = False
        self._pause_event = asyncio.Event()
        self._pause_event.set()  # Not paused initially
        
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
        # Wait if paused
        await self._pause_event.wait()
        
        try:
            # Convert string to callable if needed
            fn = eval(self.config.objective_fn) if isinstance(self.config.objective_fn, str) else self.config.objective_fn
            # Call objective function with unpacked parameters
            result = fn(**candidate)
            return float(result)
        except Exception as e:
            logger.error(f"Error evaluating candidate: {str(e)}")
            # Re-raise the original exception to preserve the error message
            raise e from None
            
    async def pause(self) -> None:
        """Pause the optimization process.
        
        This will pause after the current evaluation is complete.
        """
        if not self._paused:
            self._paused = True
            self._pause_event.clear()
            logger.info("Optimization paused")
            
    async def resume(self) -> None:
        """Resume the optimization process."""
        if self._paused:
            self._paused = False
            self._pause_event.set()
            logger.info("Optimization resumed")
            
    async def cleanup(self) -> None:
        """Clean up resources used by the optimizer.
        
        This includes stopping any running processes and cleaning up multiprocessing resources.
        """
        # Ensure optimization is not paused
        if self._paused:
            await self.resume()
            
        # Clean up nevergrad optimizer resources
        if hasattr(self, '_optimizer') and self._optimizer is not None:
            # Cancel any pending evaluations
            self._optimizer.tell_not_asked = None  # type: ignore
            self._optimizer._asked = {}  # type: ignore
            self._optimizer._num_ask = 0  # type: ignore
            self._optimizer._num_tell = 0  # type: ignore
            
        logger.info("Optimizer resources cleaned up") 