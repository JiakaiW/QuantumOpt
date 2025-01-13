from typing import Optional, Dict, Any, Callable
import os
import logging
import time
from datetime import datetime
import pickle
from abc import ABC, abstractmethod
from multiprocessing import Pool
from ..visualization.progress_tracking import OptimizationProgressTracker

class BaseParallelOptimizer(ABC):
    """Base class for parallel optimization implementations."""
    
    def __init__(self,
                 objective_fn: Callable,
                 parameter_config: Dict[str, Dict[str, Any]],
                 optimizer_config: Dict[str, Any],
                 execution_config: Dict[str, Any]):
        """Initialize base optimizer.
        
        Args:
            objective_fn: Function to optimize
            parameter_config: Configuration for parameters being optimized
            optimizer_config: Configuration for the optimizer
            execution_config: Configuration for execution environment
                {
                    "checkpoint_dir": str,     # Directory for checkpoints
                    "log_file": str,           # Log file path
                    "precompile": bool,        # Whether to precompile functions
                    "log_level": str           # Logging level
                }
        """
        self.objective_fn = objective_fn
        self.parameter_config = parameter_config
        self.optimizer_config = optimizer_config
        self.execution_config = execution_config
        
        # Set up directories
        os.makedirs(execution_config["checkpoint_dir"], exist_ok=True)
        
        # Set up logging
        self._setup_logging()
        
        # Set up progress tracking
        self._setup_progress_tracking()
    
    def _setup_logging(self):
        """Configure logging."""
        log_file = self.execution_config.get("log_file", "optimization.log")
        log_level = self.execution_config.get("log_level", "INFO")
        
        logging.basicConfig(
            filename=log_file,
            level=getattr(logging, log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        self.logger = logging.getLogger(self.__class__.__name__)
        self.logger.info(f"Initializing {self.__class__.__name__}")
    
    def _setup_progress_tracking(self):
        """Set up progress tracker."""
        self.progress_tracker = OptimizationProgressTracker(
            title=f"{self.__class__.__name__} Progress",
            parameter_config=self.parameter_config,
            budget=self.optimizer_config.get("budget", float('inf')),
            display_config=self.execution_config.get("display_config")
        )
    
    @abstractmethod
    def init_worker(self):
        """Initialize worker process. Must be implemented by subclasses."""
        pass
    
    @abstractmethod
    def optimize(self, **kwargs):
        """Run optimization. Must be implemented by subclasses."""
        pass
    
    def _save_checkpoint(self, state: Dict[str, Any], identifier: str):
        """Save optimization state to checkpoint."""
        checkpoint_path = os.path.join(
            self.execution_config["checkpoint_dir"],
            f"checkpoint_{identifier}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pkl"
        )
        
        with open(checkpoint_path, 'wb') as f:
            pickle.dump(state, f)
        
        self.logger.info(f"Saved checkpoint to {checkpoint_path}")
    
    def _load_checkpoint(self, identifier: str) -> Optional[Dict[str, Any]]:
        """Load latest checkpoint for given identifier."""
        checkpoint_dir = self.execution_config["checkpoint_dir"]
        checkpoints = [
            f for f in os.listdir(checkpoint_dir)
            if f.startswith(f"checkpoint_{identifier}_") and f.endswith(".pkl")
        ]
        
        if not checkpoints:
            return None
        
        # Get most recent checkpoint
        latest_checkpoint = max(checkpoints)
        checkpoint_path = os.path.join(checkpoint_dir, latest_checkpoint)
        
        with open(checkpoint_path, 'rb') as f:
            state = pickle.load(f)
        
        self.logger.info(f"Loaded checkpoint from {checkpoint_path}")
        return state
    
    def _configure_environment(self):
        """Configure environment variables and settings for worker processes."""
        # This can be overridden by subclasses to set specific environment variables
        pass
    
    def _precompile_functions(self):
        """Precompile functions if needed."""
        # This should be overridden by subclasses that need function precompilation
        pass 