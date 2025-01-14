"""Tests for optimization functionality."""
import asyncio
import time
from typing import List, Dict, Any
from unittest.mock import Mock, patch

import pytest

from quantum_opt.utils.events import Event, EventType
from quantum_opt.queue.task import OptimizationTask
from quantum_opt.optimizers.optimization_schemas import OptimizationConfig
from quantum_opt.optimizers.global_optimizer import MultiprocessingGlobalOptimizer

@pytest.fixture
def optimization_config() -> OptimizationConfig:
    """Create a test optimization configuration."""
    parameter_config = {
        "x": {"lower_bound": -2.0, "upper_bound": 2.0, "scale": "linear"},
        "y": {"lower_bound": -2.0, "upper_bound": 2.0, "scale": "linear"}
    }
    optimizer_config = {
        "type": "cma",
        "budget": 100,
        "batch_size": 10
    }
    objective_fn = "lambda x, y: (x - 1.0)**2 + (y - 1.0)**2"
    return OptimizationConfig(
        name="test_optimization",
        parameter_config=parameter_config,
        optimizer_config=optimizer_config,
        objective_fn=objective_fn,
        objective_fn_source=objective_fn
    )

@pytest.fixture
def optimizer_config() -> Dict[str, Any]:
    """Create a test optimizer configuration."""
    return {
        "optimizer_type": "OnePlusOne",
        "budget": 100,
        "num_workers": 4
    }

class TestOptimizationTask:
    """Test optimization task functionality."""

    @pytest.mark.asyncio
    async def test_task_initialization(self, optimization_config: OptimizationConfig):
        """Test task initialization."""
        task = OptimizationTask(task_id="test_task", config=optimization_config)
        assert task.task_id == "test_task"
        assert task.status == "pending"
        assert task.result is None
        assert task.error is None

    @pytest.mark.asyncio
    async def test_task_state_transitions(self, optimization_config: OptimizationConfig):
        """Test task state transitions."""
        task = OptimizationTask(task_id="test_task", config=optimization_config)
        assert task.status == "pending"

        # Create a mock optimizer that will delay completion
        mock_optimizer = Mock(spec=MultiprocessingGlobalOptimizer)
        async def mock_optimize():
            await asyncio.sleep(0.5)  # Delay completion
            return {"best_value": 0.0, "best_params": {"x": 1.0, "y": 1.0}}
        mock_optimizer.optimize = mock_optimize
        mock_optimizer.add_subscriber = Mock()

        # Patch the optimizer creation
        with patch('quantum_opt.queue.task.MultiprocessingGlobalOptimizer', return_value=mock_optimizer):
            # Start task
            await task.start()
            await asyncio.sleep(0.1)  # Allow task to start
            assert task.status == "running"

            # Test pause/resume
            await task.pause()
            assert task.status == "paused"

            await task.resume()
            assert task.status == "running"

            # Test stop
            await task.stop()
            assert task.status == "stopped"

    @pytest.mark.asyncio
    async def test_task_events(self, optimization_config: OptimizationConfig):
        """Test task event emission."""
        task = OptimizationTask(task_id="test_task", config=optimization_config)
        events: List[Event] = []

        async def event_handler(event: Event):
            events.append(event)

        task.add_subscriber(event_handler)

        # Start task and collect events
        await task.start()
        await asyncio.sleep(0.1)  # Allow some events to be processed

        # Verify events
        event_types = [e.event_type for e in events]
        assert EventType.TASK_STARTED in event_types
        assert EventType.TASK_STATUS_CHANGED in event_types

    @pytest.mark.asyncio
    async def test_optimization_progress(self, optimization_config: OptimizationConfig):
        """Test optimization progress tracking."""
        # Create task
        task = OptimizationTask(task_id="test_task", config=optimization_config)
        events: List[Event] = []

        async def event_handler(event: Event):
            events.append(event)

        task.add_subscriber(event_handler)

        # Start task and collect events
        await task.start()
        
        # Wait for at least 3 events or timeout after 5 seconds
        start_time = time.time()
        while len(events) < 3 and time.time() - start_time < 5:
            await asyncio.sleep(0.1)

        # Stop task if not completed
        if task.status != "completed":
            await task.stop()

        # Verify events were received
        assert len(events) > 0, "No events received"
        assert task.result is not None, "Task has no results"
        assert len(task.result.get("optimization_trace", [])) > 0, "No optimization trace"

        # Print debug info
        print(f"Optimization trace length: {len(task.result['optimization_trace'])}")
        print(f"First few trace points: {task.result['optimization_trace'][:3]}")

    @pytest.mark.asyncio
    async def test_optimization_convergence(self, optimization_config: OptimizationConfig):
        """Test that optimization converges to known minimum."""
        task = OptimizationTask(task_id="test_task", config=optimization_config)
        
        # Start optimization
        await task.start()
        
        # Wait for completion or timeout
        for _ in range(50):  # 5 second timeout
            if task.status == "completed":
                break
            await asyncio.sleep(0.1)
        
        assert task.status == "completed"
        assert task.result is not None
        
        # Check convergence
        best_params = task.result["best_params"]
        best_value = task.result["best_value"]
        
        # Should be close to minimum at (1, 1)
        assert abs(best_params["x"] - 1.0) < 0.1
        assert abs(best_params["y"] - 1.0) < 0.1
        assert best_value < 0.01  # Should be close to 0
        
    @pytest.mark.asyncio
    async def test_multiple_optimizations(self, optimization_config: OptimizationConfig):
        """Test running multiple optimization tasks concurrently."""
        # Update config to use CMA with more budget for better convergence
        optimization_config.optimizer_config.optimizer_type = "CMA"
        optimization_config.optimizer_config.budget = 200
        optimization_config.optimizer_config.num_workers = 2

        num_tasks = 3
        tasks = [
            OptimizationTask(task_id=f"task_{i}", config=optimization_config)
            for i in range(num_tasks)
        ]
        
        # Start all tasks
        await asyncio.gather(*(task.start() for task in tasks))
        
        # Wait for completion or timeout
        for _ in range(100):  # 10 second timeout
            if all(task.status == "completed" for task in tasks):
                break
            await asyncio.sleep(0.1)
        
        # Verify all tasks completed successfully
        for task in tasks:
            assert task.status == "completed"
            assert task.result is not None
            assert task.result["best_value"] < 0.5  # More realistic convergence threshold
            
            # Check that parameters are in reasonable range
            best_params = task.result["best_params"]
            assert abs(best_params["x"] - 1.0) < 1.0  # Within 1.0 of optimal
            assert abs(best_params["y"] - 1.0) < 1.0  # Within 1.0 of optimal

class TestOptimizer:
    """Test suite for MultiprocessingGlobalOptimizer."""
    
    @pytest.mark.asyncio
    async def test_optimizer_creation(self, optimization_config: OptimizationConfig):
        """Test optimizer initialization."""
        optimizer = MultiprocessingGlobalOptimizer(optimization_config)
        assert optimizer.config == optimization_config
        
    @pytest.mark.asyncio
    async def test_optimizer_events(self, optimization_config: OptimizationConfig):
        """Test optimizer event emission."""
        optimizer = MultiprocessingGlobalOptimizer(optimization_config)
        events: List[Event] = []
        
        async def event_handler(event: Event):
            events.append(event)
            
        optimizer.add_subscriber(event_handler)
        
        # Run optimization
        result = await optimizer.optimize()
        
        # Verify events
        assert len(events) > 0
        assert any(e.event_type == EventType.ITERATION_COMPLETED for e in events)
        
        # Check result structure
        assert "best_value" in result
        assert "best_params" in result
        assert "total_evaluations" in result
        
    @pytest.mark.asyncio
    async def test_optimizer_parameter_bounds(self, optimization_config: OptimizationConfig):
        """Test that optimizer respects parameter bounds."""
        optimizer = MultiprocessingGlobalOptimizer(optimization_config)
        result = await optimizer.optimize()
        
        # Check that parameters are within bounds
        for param_name, param_config in optimization_config.parameter_config.items():
            value = result["best_params"][param_name]
            assert param_config.lower_bound <= value <= param_config.upper_bound
            
    @pytest.mark.asyncio
    async def test_optimizer_budget(self, optimization_config: OptimizationConfig):
        """Test that optimizer respects the evaluation budget."""
        optimizer = MultiprocessingGlobalOptimizer(optimization_config)
        result = await optimizer.optimize()
        
        # Check that we didn't exceed budget
        assert result["total_evaluations"] <= optimization_config.optimizer_config.budget 