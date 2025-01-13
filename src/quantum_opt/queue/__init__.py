"""Task queue management for QuantumOpt."""
from .task import OptimizationTask
from .manager import TaskQueue

__all__ = ['OptimizationTask', 'TaskQueue'] 