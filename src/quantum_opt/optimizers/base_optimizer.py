"""Base class for parallel optimizers."""
import asyncio
import logging
from typing import Dict, Any, Optional, List, Tuple

import nevergrad as ng

from ..utils.events import EventEmitter, EventType, Event, create_task_event
from .optimization_schemas import OptimizationConfig

logger = logging.getLogger(__name__)

class BaseParallelOptimizer(EventEmitter):
    """Base class for parallel optimizers."""
    
    def __init__(self, config: OptimizationConfig, task_id: Optional[str] = None):
        """Initialize base optimizer.
        
        Args:
            config: Optimizer configuration containing parameter bounds, optimizer settings,
                   and objective function
            task_id: Optional task ID for event tracking
        """
        super().__init__()
        self.config = config
        self.task_id = task_id
        self._stopped = False
        self._optimizer: Optional[ng.optimizers.base.Optimizer] = None
        self._best_value = float('inf')
        self._best_params = None
        
    async def optimize(self) -> Dict[str, Any]:
        """Run the optimization process.
        
        Returns:
            Dict[str, Any]: The optimization result containing:
                - best_params: Parameters giving best result
                - best_value: Best objective value found
                - total_evaluations: Number of evaluations completed
            
        Raises:
            RuntimeError: If optimization fails
            ValueError: If candidate evaluation fails
        """
        try:
            # Create optimizer
            optimizer = self._create_optimizer()
            if optimizer is None:
                raise RuntimeError("Failed to create optimizer")
            self._optimizer = optimizer
                
            # Get number of workers and budget
            num_workers = self.config.optimizer_config.num_workers
            remaining_budget = self.config.optimizer_config.budget
            
            while not self._stopped and remaining_budget > 0:
                # Ask for candidates
                candidates = []
                for _ in range(min(num_workers, remaining_budget)):
                    try:
                        candidate = self._optimizer.ask()
                        candidates.append(candidate)
                    except Exception as e:
                        logger.error(f"Error asking for candidate: {e}")
                        raise RuntimeError(f"Failed to generate candidate: {e}")
                
                if not candidates:
                    break
                
                # Evaluate candidates
                try:
                    # Create evaluation tasks
                    eval_tasks = [
                        self._evaluate_candidate_wrapper(candidate)
                        for candidate in candidates
                    ]
                    
                    # Wait for all evaluations to complete
                    results = await asyncio.gather(*eval_tasks, return_exceptions=True)
                    
                    # Process results
                    for candidate, result in zip(candidates, results):
                        if isinstance(result, Exception):
                            # Re-raise the exception to stop optimization
                            raise result
                            
                        # Update optimizer
                        value = float(result)
                        self._optimizer.tell(candidate, value)
                        remaining_budget -= 1
                        
                        # Update best result
                        if value < self._best_value:
                            self._best_value = value
                            self._best_params = candidate.kwargs
                            
                            # Emit event
                            if self.task_id:
                                await self.emit(create_task_event(
                                    event_type=EventType.ITERATION_COMPLETED,
                                    task_id=self.task_id,
                                    best_x=self._best_params,
                                    best_y=self._best_value
                                ))
                        
                        # Always emit iteration event
                        await self.emit(create_task_event(
                            event_type=EventType.ITERATION_COMPLETED,
                            task_id=self.task_id or "test",
                            best_x=self._best_params or candidate.kwargs,
                            best_y=self._best_value
                        ))
                                
                except Exception as e:
                    logger.error(f"Error processing batch: {e}")
                    raise
                    
            # Return best result
            return {
                "best_params": self._best_params,
                "best_value": self._best_value,
                "total_evaluations": self._optimizer.num_tell
            }
            
        except Exception as e:
            logger.error(f"Error during optimization: {e}")
            raise
            
    async def _evaluate_candidate_wrapper(self, candidate: ng.p.Parameter) -> float:
        """Wrapper for candidate evaluation that extracts parameters.
        
        Args:
            candidate: The candidate to evaluate
            
        Returns:
            float: The objective function value
            
        Raises:
            Exception: If evaluation fails
        """
        try:
            # Extract parameters from candidate
            params = candidate.kwargs
            
            # Evaluate objective function
            return await self._evaluate_candidate(params)
        except Exception as e:
            logger.error(f"Error evaluating candidate: {e}")
            raise
            
    def stop(self) -> None:
        """Stop the optimization process."""
        self._stopped = True
        
    def _create_optimizer(self) -> ng.optimizers.base.Optimizer:
        """Create and return an optimizer instance.
        
        This method should be implemented by subclasses.
        """
        raise NotImplementedError
        
    async def _evaluate_candidate(self, candidate: Dict[str, Any]) -> float:
        """Evaluate a candidate solution.
        
        This method should be implemented by subclasses.
        
        Args:
            candidate: Dictionary of parameter values to evaluate
            
        Returns:
            float: The objective function value
            
        Raises:
            Exception: If evaluation fails
        """
        raise NotImplementedError 