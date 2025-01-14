"""Task implementation for optimization."""
import asyncio
import logging
from typing import Optional, Dict, Any, List, Set, Callable, Union, Awaitable
import time
import json

from ..optimizers import MultiprocessingGlobalOptimizer
from ..optimizers.optimization_schemas import OptimizationConfig, ParameterConfig, OptimizerConfig
from ..utils.events import EventEmitter, Event, EventType, create_task_event, create_optimization_event

logger = logging.getLogger(__name__)

class OptimizationTask(EventEmitter):
    """Task implementation for optimization."""
    
    def __init__(self, task_id: str, config: Union[OptimizationConfig, str]):
        """Initialize optimization task.
        
        Args:
            task_id: Unique identifier for the task
            config: Configuration for the optimization, either as an OptimizationConfig object
                   or a JSON string
        """
        super().__init__()
        self.task_id = task_id
        
        # Parse config if it's a string
        if isinstance(config, str):
            config_dict = json.loads(config)
            # If objective_fn_source is provided, execute it to define the function
            if "objective_fn_source" in config_dict:
                # Create a new namespace to avoid polluting globals
                namespace = {}
                exec(config_dict["objective_fn_source"], namespace)
                config_dict["objective_fn"] = namespace[config_dict["objective_fn"]]
            config = OptimizationConfig(**config_dict)
        self.config = config
        self.result = None
        self.status = "pending"
        self._stop_requested = False
        self._pause_requested = False
        self._optimizer = None
        
        self.error = None
        
        self._optimization_task: Optional[asyncio.Task] = None
        
    async def _cleanup_optimizer(self) -> None:
        """Clean up optimizer resources."""
        if self._optimizer:
            try:
                await self._optimizer.cleanup()
            except (TypeError, AttributeError):
                # If cleanup is not async or not available, try non-async version
                try:
                    self._optimizer.cleanup()
                except (AttributeError, NotImplementedError):
                    pass
            self._optimizer = None
        
    async def _update_status(self, new_status: str) -> None:
        """Update the task status and emit a status change event."""
        old_status = self.status
        self.status = new_status
        await self.emit(create_task_event(
            EventType.TASK_STATUS_CHANGED, 
            self.task_id,
            old_status=old_status,
            new_status=new_status
        ))
        
    async def start(self) -> None:
        """Start the optimization task."""
        if self.status != "pending":
            raise ValueError(f"Cannot start task in {self.status} state")
        
        # Initialize result dictionary
        self.result = {
            "optimization_trace": [],
            "best_value": float('inf'),
            "best_params": None,
            "total_evaluations": 0,
            "start_time": time.time(),
            "end_time": None
        }
        
        # Emit TASK_STARTED event before changing status
        await self.emit(create_task_event(EventType.TASK_STARTED, self.task_id))
        
        # Update status and start optimization
        await self._update_status("running")
        self._optimization_task = asyncio.create_task(self._run_optimization())
        
    async def stop(self) -> None:
        """Stop the optimization task."""
        if self.status == "completed":
            # Task is already completed, nothing to do
            return
            
        if self.status not in ["running", "paused"]:
            raise ValueError(f"Cannot stop task in {self.status} state")
            
        self._stop_requested = True
        if self._optimization_task:
            self._optimization_task.cancel()
            try:
                await self._optimization_task
            except asyncio.CancelledError:
                pass
            
        # Clean up optimizer resources
        await self._cleanup_optimizer()
        self.result["end_time"] = time.time()
        await self._update_status("stopped")
        
    async def pause(self) -> None:
        """Pause the optimization task."""
        if self.status != "running":
            raise ValueError(f"Cannot pause task in {self.status} state")
            
        self._pause_requested = True
        if self._optimizer:
            try:
                await self._optimizer.pause()
            except (TypeError, AttributeError):
                # If pause is not async or not available, try non-async version
                self._optimizer.pause()
        await self._update_status("paused")
        
    async def resume(self) -> None:
        """Resume the optimization task."""
        if self.status != "paused":
            raise ValueError(f"Cannot resume task in {self.status} state")
            
        self._pause_requested = False
        if self._optimizer:
            try:
                await self._optimizer.resume()
            except (TypeError, AttributeError):
                # If resume is not async or not available, try non-async version
                self._optimizer.resume()
        await self._update_status("running")
        
    async def _run_optimization(self) -> None:
        """Run the optimization process."""
        try:
            if not self._optimizer:
                self._optimizer = MultiprocessingGlobalOptimizer(self.config)
                
                # Subscribe to optimizer events
                async def handle_optimizer_event(event: Event) -> None:
                    if event.event_type == EventType.ITERATION_COMPLETED:
                        current_value = event.data.get("value")
                        current_params = event.data.get("params", {})
                        best_value = event.data.get("best_value")
                        best_params = event.data.get("best_params", {})
                        total_evaluations = event.data.get("total_evaluations", 0)
                        
                        # Update result with best values
                        if best_value is not None and best_value < self.result["best_value"]:
                            self.result["best_value"] = best_value
                            self.result["best_params"] = best_params
                        
                        # Update total evaluations
                        self.result["total_evaluations"] = total_evaluations
                        
                        # Update optimization trace
                        trace_point = {
                            "iteration": len(self.result["optimization_trace"]),
                            "value": current_value,
                            "best_value": best_value,
                            "params": current_params,
                            "best_params": best_params,
                            "total_evaluations": total_evaluations,
                            "timestamp": time.time()
                        }
                        self.result["optimization_trace"].append(trace_point)
                        
                        # Emit progress event
                        await self.emit(create_optimization_event(
                            EventType.OPTIMIZATION_PROGRESS,
                            self.task_id,
                            value=current_value,
                            best_value=best_value,
                            best_params=best_params,
                            current_params=current_params,
                            total_evaluations=total_evaluations
                        ))
                
                # Add subscriber to optimizer
                try:
                    await self._optimizer.add_subscriber(handle_optimizer_event)
                except (TypeError, AttributeError):
                    # If add_subscriber is not async or not available, try non-async version
                    self._optimizer.add_subscriber(handle_optimizer_event)
            
            # Run optimization
            try:
                # Check if we should continue
                if self._stop_requested:
                    return
                    
                result = await self._optimizer.optimize()
                if asyncio.iscoroutine(result):
                    result = await result
                
                # Check if we were stopped during optimization
                if self._stop_requested:
                    return
                    
                if self.status != "stopped":
                    # Add final point to trace if not already present
                    if not self.result["optimization_trace"]:
                        trace_point = {
                            "iteration": 0,
                            "value": result.get("best_value", float('inf')),
                            "best_value": result.get("best_value", float('inf')),
                            "params": result.get("best_params", {}),
                            "best_params": result.get("best_params", {}),
                            "total_evaluations": result.get("total_evaluations", 0),
                            "timestamp": time.time()
                        }
                        self.result["optimization_trace"].append(trace_point)
                    
                    # Update final results
                    self.result["best_value"] = result.get("best_value", self.result["best_value"])
                    self.result["best_params"] = result.get("best_params", self.result["best_params"])
                    self.result["total_evaluations"] = result.get("total_evaluations", self.result["total_evaluations"])
                    self.result["end_time"] = time.time()
                    await self._update_status("completed")
                    
                    # Emit completion event
                    await self.emit(create_optimization_event(
                        EventType.OPTIMIZATION_COMPLETED,
                        self.task_id,
                        best_value=self.result["best_value"],
                        best_params=self.result["best_params"],
                        total_evaluations=self.result["total_evaluations"]
                    ))
            except asyncio.CancelledError:
                # Task was cancelled, don't change status as it's already stopped/paused
                raise
            except Exception as e:
                if not self._stop_requested:  # Only update status if not stopped
                    self.error = str(e)
                    await self._update_status("failed")
                    # Emit error event
                    await self.emit(create_optimization_event(
                        EventType.OPTIMIZATION_ERROR,
                        self.task_id,
                        error=str(e)
                    ))
                raise
            
        except asyncio.CancelledError:
            # Task was cancelled, don't change status as it's already stopped/paused
            raise
        except Exception as e:
            if not self._stop_requested:  # Only update status if not stopped
                self.error = str(e)
                await self._update_status("failed")
            raise 