"""Task queue management."""
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
import asyncio
import logging
import traceback
from .task import OptimizationTask
from ..optimizers.global_optimizer import MultiprocessingGlobalOptimizer

logger = logging.getLogger(__name__)

class TaskQueue:
    """Manages optimization tasks."""
    def __init__(self):
        self.tasks: Dict[str, OptimizationTask] = {}
        self.queue: List[str] = []  # Order of task IDs
        self._running: bool = False
        self._current_task: Optional[str] = None
        self._event_callbacks: List[Callable] = []

    def add_task(self, task: OptimizationTask) -> str:
        """Add a task to the queue."""
        self.tasks[task.task_id] = task
        self.queue.append(task.task_id)
        asyncio.create_task(self._notify_event("task_added", task.task_id))
        return task.task_id
    
    def get_next_task(self) -> Optional[OptimizationTask]:
        """Get the next task to run."""
        if not self.queue:
            return None
        return self.tasks[self.queue[0]]
    
    def mark_complete(self, task_id: str, result: Dict[str, Any]):
        """Mark a task as complete with results."""
        if task_id not in self.tasks:
            raise ValueError(f"Task {task_id} not found")
        
        task = self.tasks[task_id]
        task.status = 'completed'
        task.completed_at = datetime.now()
        task.result = result
        if task_id in self.queue:
            self.queue.remove(task_id)
        asyncio.create_task(self._notify_event("task_completed", task_id))
    
    def mark_failed(self, task_id: str, error: str):
        """Mark a task as failed."""
        if task_id not in self.tasks:
            raise ValueError(f"Task {task_id} not found")
        
        task = self.tasks[task_id]
        task.status = 'failed'
        task.completed_at = datetime.now()
        task.result = {"error": error}
        if task_id in self.queue:
            self.queue.remove(task_id)
        asyncio.create_task(self._notify_event("task_failed", task_id))

    def get_task(self, task_id: str) -> Optional[OptimizationTask]:
        """Get a task by ID."""
        return self.tasks.get(task_id)

    def get_all_tasks(self) -> List[OptimizationTask]:
        """Get all tasks."""
        return list(self.tasks.values())

    def subscribe(self, callback: Callable):
        """Subscribe to queue events."""
        self._event_callbacks.append(callback)

    async def _notify_event(self, event_type: str, task_id: str):
        """Notify subscribers of queue events."""
        event = {
            "type": event_type,
            "task_id": task_id,
            "task": self.tasks[task_id].to_dict()
        }
        for callback in self._event_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event)
                else:
                    callback(event)
            except Exception as e:
                logger.error(f"Error in event callback: {e}")

    async def start_processing(self):
        """Start processing tasks in the queue."""
        self._running = True
        while self._running and self.queue:
            task = self.get_next_task()
            if not task:
                break

            self._current_task = task.task_id
            task.status = 'running'
            task.started_at = datetime.now()
            await self._notify_event("task_started", task.task_id)

            try:
                # Create optimizer
                logger.info(f"Creating optimizer for task {task.task_id}")
                optimizer = MultiprocessingGlobalOptimizer(
                    objective_fn=task.objective_function,
                    parameter_config=task.parameter_config,
                    optimizer_config=task.optimizer_config,
                    execution_config=task.execution_config
                )
                
                # Run optimization
                logger.info(f"Starting optimization for task {task.task_id}")
                result = await optimizer.optimize()
                logger.info(f"Optimization complete for task {task.task_id}: {result}")
                self.mark_complete(task.task_id, result)
                
            except Exception as e:
                error_msg = f"Error processing task {task.task_id}: {str(e)}\n{traceback.format_exc()}"
                logger.error(error_msg)
                self.mark_failed(task.task_id, error_msg)

            self._current_task = None

    def stop(self):
        """Stop processing tasks."""
        self._running = False 