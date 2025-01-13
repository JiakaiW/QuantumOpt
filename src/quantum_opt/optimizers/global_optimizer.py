"""Global optimization implementation using Nevergrad."""
import asyncio
import logging
import time
import nevergrad as ng
from typing import Dict, Any, Optional
from .base_optimizer import BaseParallelOptimizer

logger = logging.getLogger(__name__)

class MultiprocessingGlobalOptimizer(BaseParallelOptimizer):
    """Implementation of parallel global optimization using Nevergrad."""
    
    def __init__(self,
                 objective_fn,
                 parameter_config: Dict[str, Dict[str, Any]],
                 optimizer_config: Dict[str, Any],
                 execution_config: Dict[str, Any]):
        """Initialize global optimizer."""
        super().__init__(objective_fn, parameter_config, optimizer_config, execution_config)
        self.setup_optimizer()

    def init_worker(self):
        """Initialize worker process."""
        pass

    def setup_optimizer(self):
        """Configure Nevergrad optimizer."""
        # Create parameter space
        param_space = {}
        for name, config in self.parameter_config.items():
            if config["type"] == "log":
                param_space[name] = ng.p.Log(
                    init=config["init"],
                    lower=config["lower"],
                    upper=config["upper"]
                )
            else:  # scalar
                param_space[name] = ng.p.Scalar(
                    init=config["init"],
                    lower=config["lower"],
                    upper=config["upper"]
                )
        
        self.parametrization = ng.p.Instrumentation(**param_space)
        
        # Create optimizer
        optimizer_name = self.optimizer_config.get("optimizer", "CMA")
        budget = self.optimizer_config.get("budget", 100)
        num_workers = self.optimizer_config.get("num_workers", 1)
        
        self.optimizer = ng.optimizers.registry[optimizer_name](
            parametrization=self.parametrization,
            budget=budget,
            num_workers=num_workers
        )

    async def optimize(self) -> Dict[str, Any]:
        """Run optimization asynchronously."""
        logger.info("Starting optimization")
        start_time = time.time()
        best_value = float('inf')
        best_params = None
        total_evaluations = 0
        
        try:
            while not self.optimizer.ask_tell_not_asked:
                # Get next parameters to evaluate
                candidate = self.optimizer.ask()
                
                # Evaluate function (with sleep for debugging)
                value = self.objective_fn(**candidate.kwargs)
                total_evaluations += 1
                
                # Update optimizer
                self.optimizer.tell(candidate, value)
                
                # Track best result
                if value < best_value:
                    best_value = value
                    best_params = candidate.kwargs
                
                # Allow other tasks to run
                await asyncio.sleep(0)
            
            optimization_time = time.time() - start_time
            
            return {
                "best_value": float(best_value),
                "best_params": {k: float(v) for k, v in best_params.items()},
                "total_evaluations": total_evaluations,
                "optimization_time": optimization_time
            }
            
        except Exception as e:
            logger.error(f"Error during optimization: {e}")
            raise 