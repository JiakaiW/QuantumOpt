"""Task queue manager for handling optimization tasks."""
import asyncio
import logging
import uuid
from typing import Dict, Any, Optional, List

from .task import OptimizationTask
from ..utils.events import EventEmitter, Event, EventType, create_task_event

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
        self._current_task: Optional[str] = None
        logger.debug("Task queue initialized")
        
    @property
    def is_processing(self) -> bool:
        """Whether the queue is currently processing tasks."""
        return not self._stopped
        
    @property
    def is_paused(self) -> bool:
        """Whether the queue is paused."""
        return self._is_paused
        
    async def add_task(self, config: Dict[str, Any]) -> None:
        """Add a task to the queue.
        
        Args:
            config: Task configuration including objective function and parameters
            
        Raises:
            ValueError: If task ID already exists in queue
        """
        try:
            # Generate task ID if not provided
            task_id = config.get("task_id", str(uuid.uuid4()))
            logger.debug(f"Adding task {task_id} to queue")
            
            if task_id in self._tasks:
                raise ValueError(f"Task {task_id} already exists in queue")
            
            # Create task instance
            task = OptimizationTask(task_id=task_id, config=config)
            self._tasks[task.task_id] = task
            task.add_subscriber(self._forward_task_event)
            logger.debug(f"Added subscriber for task {task_id}")
            
            # Forward task events to all subscribers
            for subscriber in self._subscribers:
                task.add_subscriber(subscriber)
                logger.debug(f"Added task {task_id} subscriber: {subscriber}")
            
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
        """Start processing tasks in the queue."""
        if self.is_processing:
            logger.warning("Queue is already processing")
            return
            
        logger.info("Starting task queue processing")
        self._stopped = False
        self._is_paused = False
        self._current_task = None
        self._processing_task = asyncio.create_task(self._process_tasks())
        
    async def stop_processing(self) -> None:
        """Stop processing tasks in the queue."""
        if not self.is_processing:
            return
            
        logger.info("Stopping task queue processing")
        self._stopped = True
        if self._processing_task:
            self._processing_task.cancel()
            try:
                await self._processing_task
            except asyncio.CancelledError:
                pass
            self._processing_task = None
            
        # Reset state
        self._is_paused = False
        self._current_task = None
        # Clear tasks to ensure clean state
        self._tasks.clear()
        
    async def pause_processing(self) -> None:
        """Pause task queue processing."""
        if not self.is_processing or self.is_paused:
            return
            
        logger.info("Pausing task queue processing")
        self._is_paused = True
        await self.emit(create_task_event(
            event_type=EventType.QUEUE_PAUSED,
            task_id="queue",
            status="paused"
        ))
        
    async def resume_processing(self) -> None:
        """Resume task queue processing."""
        if not self.is_processing or not self.is_paused:
            return
            
        logger.info("Resuming task queue processing")
        self._is_paused = False
        await self.emit(create_task_event(
            event_type=EventType.QUEUE_RESUMED,
            task_id="queue",
            status="running"
        ))
        
    async def _process_tasks(self) -> None:
        """Process tasks in the queue sequentially."""
        logger.info("Starting task queue processing")
        
        await self.emit(create_task_event(
            event_type=EventType.QUEUE_STARTED,
            task_id="queue",
            status="running"
        ))
        
        try:
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
                self._current_task = task.task_id
                logger.info(f"Processing task {task.task_id}")
                
                try:
                    # Start task
                    await task.start()
                    
                    # Wait for task to complete
                    while task.status == "running":
                        await asyncio.sleep(0.1)
                    
                    # Emit event after task completes
                    if task.status == "completed":
                        await self.emit(create_task_event(
                            event_type=EventType.TASK_COMPLETED,
                            task_id=task.task_id,
                            status="completed",
                            result=task.result
                        ))
                    elif task.status == "failed":
                        await self.emit(create_task_event(
                            event_type=EventType.TASK_FAILED,
                            task_id=task.task_id,
                            status="failed",
                            error=task.error
                        ))
                except Exception as e:
                    logger.error(f"Error processing task {task.task_id}: {e}")
                    await self.emit(create_task_event(
                        event_type=EventType.TASK_FAILED,
                        task_id=task.task_id,
                        status="failed",
                        error=str(e)
                    ))
                finally:
                    self._current_task = None
                    
        except asyncio.CancelledError:
            logger.info("Task processing cancelled")
            raise
        finally:
            self._current_task = None
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
        logger.debug(f"Forwarding task event: {event.to_dict()}")
        await self.emit(event)
    
    async def start_task(self, task_id: str) -> bool:
        """Start a specific task.
        
        Args:
            task_id: The task ID to start
            
        Returns:
            bool: True if task was started, False otherwise
        """
        try:
            task = self._tasks.get(task_id)
            if task is None:
                logger.warning(f"Task {task_id} not found")
                return False
            
            # Start the task
            await task.start()
            logger.info(f"Started task {task_id}")
            return True
        except Exception as e:
            logger.error(f"Error starting task {task_id}: {e}")
            return False 