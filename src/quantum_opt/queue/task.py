"""Optimization task class for managing individual optimization runs."""
import asyncio
import logging
from typing import Dict, Any, Optional
from ..utils.events import EventEmitter, EventType, Event, create_task_event

logger = logging.getLogger(__name__)

class OptimizationTask(EventEmitter):
    """Represents a single optimization task with its configuration and state."""
    
    def __init__(self, task_id: str, config: Dict[str, Any]):
        """Initialize optimization task.
        
        Args:
            task_id: Unique identifier for the task
            config: Task configuration containing:
                - parameter_config: Parameter bounds and constraints
                - optimizer_config: Optimizer settings
                - execution_config: Runtime settings
                - objective_fn: Function to optimize
        """
        super().__init__()
        self.task_id = task_id
        self.config = config
        self.status = "pending"  # pending, running, paused, completed, failed, stopped
        self.result: Optional[Dict[str, Any]] = None
        self.error: Optional[str] = None
        self._optimizer = None
        self._optimization_task: Optional[asyncio.Task] = None
        logger.info(f"Task {task_id} initialized with config: {config}")
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary representation."""
        return {
            "task_id": self.task_id,
            "config": self.config,
            "status": self.status,
            "result": self.result,
            "error": self.error
        }
        
    async def start_optimization(self) -> Dict[str, Any]:
        """Start the optimization process.
        
        Returns:
            Dict[str, Any]: The optimization result
            
        Raises:
            RuntimeError: If task has failed or optimization fails
            ValueError: If optimizer creation fails
        """
        if self.status == "completed" and self.result is not None:
            logger.warning(f"Task {self.task_id} already completed")
            return self.result
            
        if self.status == "failed":
            logger.error(f"Task {self.task_id} previously failed")
            raise RuntimeError(f"Task failed: {self.error}")
            
        try:
            # Import optimizer here to avoid circular imports
            from ..optimizers.global_optimizer import MultiprocessingGlobalOptimizer
            
            # Create optimizer based on config
            optimizer_type = self.config.get("optimizer_config", {}).get("optimizer_type", "global")
            if optimizer_type == "global":
                self._optimizer = MultiprocessingGlobalOptimizer(self.config, task_id=self.task_id)
            else:
                raise ValueError(f"Unsupported optimizer type: {optimizer_type}")
                
            if not self._optimizer:
                raise ValueError("Failed to create optimizer")
                
            # Subscribe to optimizer events
            self._optimizer.add_subscriber(self._handle_optimizer_event)
            
            # Start optimization
            logger.info(f"Starting optimization for task {self.task_id}")
            await self._set_status("running")
            
            # Run optimization in a task to allow cancellation
            self._optimization_task = asyncio.create_task(self._optimizer.optimize())
            result = await self._optimization_task
            
            if not isinstance(result, dict):
                raise ValueError("Optimizer returned invalid result type")
                
            self.result = result
            await self._set_status("completed")
            logger.info(f"Task {self.task_id} completed successfully")
            
            return result
            
        except asyncio.CancelledError:
            await self._set_status("stopped")
            raise
            
        except Exception as e:
            self.error = str(e)
            await self._set_status("failed")
            logger.error(f"Error in task {self.task_id}: {e}")
            raise
            
    async def _handle_optimizer_event(self, event: Event) -> None:
        """Handle events from the optimizer."""
        # Add task ID to event data if not present
        if "task_id" not in event.data:
            event.data["task_id"] = self.task_id
        # Forward the event
        await self.emit(event)
        
    async def _set_status(self, status: str) -> None:
        """Update task status and emit event."""
        self.status = status
        await self.emit(create_task_event(
            event_type=EventType.TASK_STATUS_CHANGED,
            task_id=self.task_id,
            status=status,
            result=self.result if status == "completed" else None,
            error=self.error if status == "failed" else None
        ))
        
    async def pause(self) -> bool:
        """Pause the optimization process.
        
        Returns:
            bool: True if the task was paused successfully, False otherwise
        """
        if self.status != "running":
            logger.warning(f"Cannot pause task {self.task_id}: not running")
            return False
            
        if not self._optimizer:
            logger.error(f"Cannot pause task {self.task_id}: no active optimizer")
            return False
            
        try:
            self._optimizer.stop()  # This will make the optimizer stop after current iteration
            await self._set_status("paused")
            logger.info(f"Task {self.task_id} paused")
            return True
        except Exception as e:
            logger.error(f"Error pausing task {self.task_id}: {e}")
            return False
        
    async def resume(self) -> bool:
        """Resume the optimization process.
        
        Returns:
            bool: True if the task was resumed successfully, False otherwise
        """
        if self.status != "paused":
            logger.warning(f"Cannot resume task {self.task_id}: not paused")
            return False
            
        try:
            # Create new optimization task
            await self._set_status("running")
            self._optimization_task = asyncio.create_task(self.start_optimization())
            logger.info(f"Task {self.task_id} resumed")
            return True
        except Exception as e:
            logger.error(f"Error resuming task {self.task_id}: {e}")
            return False
        
    async def stop(self) -> bool:
        """Stop the optimization process.
        
        Returns:
            bool: True if the task was stopped successfully, False otherwise
        """
        if self.status in ["completed", "failed", "stopped"]:
            logger.warning(f"Cannot stop task {self.task_id}: already {self.status}")
            return False
            
        try:
            if self._optimization_task and not self._optimization_task.done():
                self._optimization_task.cancel()
                await asyncio.wait([self._optimization_task])
                
            if self._optimizer:
                self._optimizer.stop()
                self._optimizer = None
                
            await self._set_status("stopped")
            logger.info(f"Task {self.task_id} stopped")
            return True
        except Exception as e:
            logger.error(f"Error stopping task {self.task_id}: {e}")
            return False 