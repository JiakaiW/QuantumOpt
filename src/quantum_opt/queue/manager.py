"""Task queue manager for handling optimization tasks."""
import asyncio
import logging
import uuid
from typing import Dict, List, Any, Optional, Union
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
        
    async def add_task(self, config: Dict[str, Any]) -> None:
        """Add a task to the queue.
        
        Args:
            config: Task configuration including objective function and parameters
        """
        try:
            # Generate task ID if not provided
            task_id = config.get("task_id", str(uuid.uuid4()))
            
            # Create task instance
            task = OptimizationTask(task_id=task_id, config=config)
            
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
            
        except Exception as e:
            logger.error(f"Error adding task to queue: {e}")
            raise
    
    async def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task state by ID.
        
        Args:
            task_id: The task ID to retrieve
            
        Returns:
            Optional[Dict[str, Any]]: Task state dictionary if found, None otherwise
        """
        task = self._tasks.get(task_id)
        if task:
            return task.to_dict()
        return None
    
    async def list_tasks(self) -> List[Dict[str, Any]]:
        """List all tasks in the queue.
        
        Returns:
            List[Dict[str, Any]]: List of task state dictionaries
        """
        return [task.to_dict() for task in self._tasks.values()]
    
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
        return await task.stop()
    
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
    
    async def _forward_task_event(self, event: Event) -> None:
        """Forward events from tasks."""
        await self.emit(event) 