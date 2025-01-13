"""Task queue management for QuantumOpt."""
from dataclasses import dataclass
from typing import Dict, Any, Callable, Optional
from datetime import datetime
import uuid

@dataclass
class OptimizationTask:
    """Represents a single optimization task."""
    task_id: str
    name: str
    parameter_config: Dict[str, Any]
    objective_function: Callable
    optimizer_config: Dict[str, Any]
    execution_config: Dict[str, Any]
    source_code: str
    status: str = 'pending'  # pending, running, completed, failed
    created_at: datetime = datetime.now()
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary for API responses."""
        return {
            "task_id": self.task_id,
            "name": self.name,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "parameter_config": self.parameter_config,
            "optimizer_config": self.optimizer_config,
            "execution_config": self.execution_config,
            "source_code": self.source_code,
            "result": self.result
        } 