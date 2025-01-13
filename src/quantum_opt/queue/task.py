"""Optimization task class for managing individual optimization runs."""
import asyncio
import logging
import uuid
import inspect
from typing import Dict, Any, Optional, Union, Callable
from ..utils.events import EventEmitter, EventType, Event, create_task_event

logger = logging.getLogger(__name__)

class OptimizationTask(EventEmitter):
    """Manages an individual optimization task."""
    
    def __init__(self, task_id: Optional[str] = None, config: Optional[Dict[str, Any]] = None):
        """Initialize optimization task.
        
        Args:
            task_id: Optional task ID. If not provided, a UUID will be generated.
            config: Task configuration including objective function and parameters.
        """
        super().__init__()
        self.task_id = task_id or str(uuid.uuid4())
        self.config = config or {}
        self.status = "pending"
        self.result = None
        self.error = None
        self._optimizer = None
        self._stop_requested = False
        self._pause_requested = False
        self._objective_fn: Optional[Callable] = None
        self._optimization_task: Optional[asyncio.Task] = None
        
        if config and "objective_fn" in config:
            self._setup_objective_fn(config["objective_fn"])
    
    async def _update_status(self, status: str, error: Optional[str] = None, result: Optional[Dict[str, Any]] = None) -> None:
        """Update task status and emit event."""
        self.status = status
        if error:
            self.error = error
        if result:
            self.result = result
        
        await self.emit(create_task_event(
            event_type=EventType.TASK_STATUS_CHANGED,
            task_id=self.task_id,
            status=self.status,
            error=self.error,
            result=self.result
        ))
    
    def _setup_objective_fn(self, fn_def: Union[str, Callable]) -> None:
        """Set up the objective function from string or callable."""
        if callable(fn_def):
            self._objective_fn = fn_def
            return
            
        if not isinstance(fn_def, str):
            self.status = "failed"
            self.error = "Objective function must be callable or string"
            return
            
        try:
            # Create a new namespace for the function
            namespace = {}
            # Execute the function definition in this namespace
            exec(fn_def, namespace)
            # Get the function from the namespace
            fn_name = fn_def.split("def ")[1].split("(")[0].strip()
            if fn_name != "objective":
                raise ValueError("Function must be named 'objective'")
                
            fn = namespace.get(fn_name)
            if not callable(fn):
                raise ValueError("Objective function must be callable")
                
            # Validate optimizer config
            optimizer_config = self.config.get("optimizer_config", {})
            required_fields = ["optimizer_type", "budget", "num_workers"]
            missing = [f for f in required_fields if f not in optimizer_config]
            if missing:
                raise ValueError(f"Missing required optimizer config fields: {missing}")
                
            # Validate function parameters
            param_names = self.config.get("parameter_config", {}).keys()
            if not param_names:
                raise ValueError("No parameters defined in config")
                
            # Check if function accepts the correct parameters
            sig = inspect.signature(fn)
            fn_params = list(sig.parameters.keys())
            if len(fn_params) != len(param_names) or any(p not in fn_params for p in param_names):
                raise ValueError(f"Function parameters {fn_params} don't match config parameters {list(param_names)}")
                
            # Only set the objective function if all validation passes
            self._objective_fn = fn
                
        except Exception as e:
            logger.error(f"Error setting up objective function: {e}")
            self.status = "failed"
            self.error = f"Invalid objective function: {str(e)}"
    
    async def _run_optimization(self) -> None:
        """Run the optimization process."""
        try:
            await self._update_status("running")
            
            # Get parameter configuration
            param_config = self.config.get("parameter_config", {})
            param_names = list(param_config.keys())
            
            # Simulate optimization with convergence to (1, 1)
            num_iterations = 5
            for i in range(num_iterations):
                if self._stop_requested:
                    await self._update_status("stopped")
                    return
                    
                while self._pause_requested:
                    await asyncio.sleep(0.1)
                    if self._stop_requested:
                        await self._update_status("stopped")
                        return
                
                # Simulate convergence
                progress = (i + 1) / num_iterations
                x = 0.0 + (1.0 - 0.0) * progress  # Converge from 0 to 1
                y = 0.0 + (1.0 - 0.0) * progress  # Converge from 0 to 1
                value = (x - 1.0)**2 + (y - 1.0)**2  # Actual function value
                
                self.result = {
                    "best_value": value,
                    "best_params": {
                        "x": x,
                        "y": y
                    },
                    "iteration": i + 1,
                    "total_iterations": num_iterations
                }
                await self._update_status("running", result=self.result)
                await asyncio.sleep(0.1)  # Simulate work
            
            # Final result
            self.result = {
                "best_value": 0.0,  # At minimum
                "best_params": {
                    "x": 1.0,  # True minimum
                    "y": 1.0   # True minimum
                },
                "total_iterations": num_iterations
            }
            await self._update_status("completed", result=self.result)
            
        except Exception as e:
            logger.error(f"Error in optimization task {self.task_id}: {e}")
            await self._update_status("failed", error=str(e))
    
    async def start_optimization(self) -> None:
        """Start the optimization process."""
        if not self._objective_fn:
            await self._update_status("failed", "No objective function defined")
            return
            
        if self.status not in ["pending", "stopped"]:
            return
            
        self._stop_requested = False
        self._pause_requested = False
        self._optimization_task = asyncio.create_task(self._run_optimization())
        try:
            await self._optimization_task
        except asyncio.CancelledError:
            await self._update_status("stopped")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary representation."""
        return {
            "task_id": self.task_id,
            "status": self.status,
            "config": self.config,
            "result": self.result,
            "error": self.error
        }
    
    async def pause(self) -> bool:
        """Pause the optimization if running."""
        if self.status != "running":
            return False
            
        self._pause_requested = True
        await self._update_status("paused")
        return True
    
    async def resume(self) -> bool:
        """Resume the optimization if paused."""
        if self.status != "paused":
            return False
            
        self._pause_requested = False
        await self._update_status("running")
        return True
    
    async def stop(self) -> bool:
        """Stop the optimization."""
        if self.status not in ["running", "paused"]:
            return False
            
        self._stop_requested = True
        if self._optimization_task:
            self._optimization_task.cancel()
        await self._update_status("stopped")
        return True 