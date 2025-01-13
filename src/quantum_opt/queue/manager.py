"""Task queue manager for handling optimization tasks."""
import asyncio
import logging
from typing import Dict, List, Any, Optional, Callable, Awaitable
from .task import OptimizationTask
from ..utils.events import EventEmitter, EventType, Event, create_task_event

logger = logging.getLogger(__name__)

class TaskQueue(EventEmitter):
    """Manages a queue of optimization tasks."""
    
    def __init__(self):
        """Initialize task queue."""
        super().__init__()
        self._tasks: Dict[str, OptimizationTask] = {}
        self._processing_task: Optional[asyncio.Task] = None
        self._stopped = True
        self._is_paused = False
        
    async def add_task(self, task: OptimizationTask) -> None:
        """Add a task to the queue.
        
        Args:
            task: The optimization task to add
        """
        if task.task_id in self._tasks:
            logger.warning(f"Task {task.task_id} already exists in queue")
            return
            
        self._tasks[task.task_id] = task
        task.add_subscriber(self._forward_task_event)
        logger.info(f"Added task {task.task_id} to queue")
        
        await self.emit(create_task_event(
            event_type=EventType.TASK_ADDED,
            task_id=task.task_id,
            status=task.status
        ))
        
    async def list_tasks(self) -> List[Dict[str, Any]]:
        """List all tasks in the queue.
        
        Returns:
            List[Dict[str, Any]]: List of task dictionaries
        """
        return [task.to_dict() for task in self._tasks.values()]
        
    async def get_task(self, task_id: str) -> Optional[OptimizationTask]:
        """Get a task by ID.
        
        Args:
            task_id: The task ID to look up
            
        Returns:
            Optional[OptimizationTask]: The task if found, None otherwise
        """
        return self._tasks.get(task_id)
        
    async def remove_task(self, task_id: str) -> bool:
        """Remove a task from the queue.
        
        Args:
            task_id: The task ID to remove
            
        Returns:
            bool: True if task was removed, False otherwise
        """
        if task_id not in self._tasks:
            logger.warning(f"Task {task_id} not found in queue")
            return False
            
        task = self._tasks[task_id]
        if task.status == "running":
            await self.stop_task(task_id)
            
        del self._tasks[task_id]
        logger.info(f"Removed task {task_id} from queue")
        
        await self.emit(create_task_event(
            event_type=EventType.TASK_REMOVED,
            task_id=task_id,
            status="removed"
        ))
        return True
        
    async def start_processing(self) -> None:
        """Start processing tasks in the queue sequentially."""
        logger.info("Starting task queue processing")
        self._stopped = False
        self._is_paused = False
        
        await self.emit(create_task_event(
            event_type=EventType.QUEUE_STARTED,
            task_id="queue",
            status="running"
        ))
        
        while not self._stopped:
            if self._is_paused:
                await asyncio.sleep(0.1)
                continue
                
            # Find next pending task
            pending_tasks = [
                task for task in self._tasks.values()
                if task.status == "pending"
            ]
            
            if not pending_tasks:
                await asyncio.sleep(0.1)
                continue
                
            # Process next task
            task = pending_tasks[0]
            try:
                await task.start_optimization()
            except Exception as e:
                logger.error(f"Error processing task {task.task_id}: {e}")
                
        await self.emit(create_task_event(
            event_type=EventType.QUEUE_STOPPED,
            task_id="queue",
            status="stopped"
        ))
        
    async def stop_task(self, task_id: str) -> bool:
        """Stop a specific task.
        
        Args:
            task_id: The task ID to stop
            
        Returns:
            bool: True if task was stopped, False otherwise
        """
        if task_id not in self._tasks:
            logger.warning(f"Task {task_id} not found in queue")
            return False
            
        task = self._tasks[task_id]
        success = await task.stop()
        if success:
            task._optimizer = None  # Ensure optimizer is cleared
        return success
        
    async def pause_task(self, task_id: str) -> bool:
        """Pause a specific task.
        
        Args:
            task_id: The task ID to pause
            
        Returns:
            bool: True if task was paused, False otherwise
        """
        if task_id not in self._tasks:
            logger.warning(f"Task {task_id} not found in queue")
            return False
            
        task = self._tasks[task_id]
        return await task.pause()
        
    async def resume_task(self, task_id: str) -> bool:
        """Resume a specific task.
        
        Args:
            task_id: The task ID to resume
            
        Returns:
            bool: True if task was resumed, False otherwise
        """
        if task_id not in self._tasks:
            logger.warning(f"Task {task_id} not found in queue")
            return False
            
        task = self._tasks[task_id]
        return await task.resume()
        
    async def pause_all(self) -> None:
        """Pause all running tasks."""
        self._is_paused = True
        for task in self._tasks.values():
            if task.status == "running":
                await task.pause()
                
    async def resume_all(self) -> None:
        """Resume all paused tasks."""
        self._is_paused = False
        for task in self._tasks.values():
            if task.status == "paused":
                await task.resume()
                
    async def stop_all(self) -> None:
        """Stop all tasks and the queue."""
        self._stopped = True
        for task in list(self._tasks.values()):
            await self.stop_task(task.task_id)
            
        await self.emit(create_task_event(
            event_type=EventType.QUEUE_STOPPED,
            task_id="queue",
            status="stopped"
        ))
        
    async def _forward_task_event(self, event: Event) -> None:
        """Forward events from tasks."""
        await self.emit(event) 