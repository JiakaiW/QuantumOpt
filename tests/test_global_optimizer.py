"""Tests for the global optimizer implementation."""

import pytest
import numpy as np
from quantum_opt.optimizers import MultiprocessingGlobalOptimizer
from quantum_opt.utils.event_system import OptimizationEventSystem


def rosenbrock(x, y):
    """Rosenbrock function for testing optimization."""
    return (1 - x) ** 2 + 100 * (y - x ** 2) ** 2


def test_global_optimizer_basic():
    """Test basic optimization functionality."""
    # Configure optimizer
    parameter_config = {
        "x": {
            "type": "scalar",
            "init": 0.0,
            "lower": -2.0,
            "upper": 2.0,
            "display_name": "X",
            "format": ".4f",
        },
        "y": {
            "type": "scalar",
            "init": 0.0,
            "lower": -2.0,
            "upper": 2.0,
            "display_name": "Y",
            "format": ".4f",
        }
    }
    
    optimizer_config = {
        "optimizer": "CMA",
        "budget": 100,
        "num_workers": 2,
    }
    
    execution_config = {
        "checkpoint_dir": None,  # Disable checkpointing for tests
        "log_file": None,       # Disable logging for tests
    }
    
    # Create optimizer
    optimizer = MultiprocessingGlobalOptimizer(
        objective_fn=lambda **kwargs: rosenbrock(**kwargs),
        parameter_config=parameter_config,
        optimizer_config=optimizer_config,
        execution_config=execution_config
    )
    
    # Run optimization
    results = optimizer.optimize()
    
    # Check results
    assert "best_value" in results
    assert "best_params" in results
    assert "total_evaluations" in results
    assert results["total_evaluations"] <= optimizer_config["budget"]
    
    # Check if optimization found the minimum (1, 1)
    best_x = results["best_params"]["x"]
    best_y = results["best_params"]["y"]
    assert abs(best_x - 1.0) < 0.1
    assert abs(best_y - 1.0) < 0.1


def test_global_optimizer_with_events():
    """Test optimizer with event system integration."""
    event_system = OptimizationEventSystem()
    events_received = []
    
    def event_callback(data):
        events_received.append(data)
    
    event_system.subscribe("ITERATION_COMPLETE", event_callback)
    
    # Configure optimizer
    parameter_config = {
        "x": {"type": "scalar", "init": 0.0, "lower": -2.0, "upper": 2.0},
        "y": {"type": "scalar", "init": 0.0, "lower": -2.0, "upper": 2.0},
    }
    
    optimizer = MultiprocessingGlobalOptimizer(
        objective_fn=lambda **kwargs: rosenbrock(**kwargs),
        parameter_config=parameter_config,
        optimizer_config={"optimizer": "CMA", "budget": 10, "num_workers": 1},
        execution_config={},
        event_system=event_system
    )
    
    # Run optimization
    optimizer.optimize()
    
    # Check events
    assert len(events_received) > 0


def test_global_optimizer_pause_resume():
    """Test pause/resume functionality."""
    event_system = OptimizationEventSystem()
    iterations_before_pause = 0
    total_iterations = 0
    
    def count_iterations(data):
        nonlocal iterations_before_pause, total_iterations
        if not event_system.is_paused():
            iterations_before_pause += 1
        total_iterations += 1
    
    event_system.subscribe("ITERATION_COMPLETE", count_iterations)
    
    # Configure optimizer
    parameter_config = {
        "x": {"type": "scalar", "init": 0.0, "lower": -2.0, "upper": 2.0},
        "y": {"type": "scalar", "init": 0.0, "lower": -2.0, "upper": 2.0},
    }
    
    optimizer = MultiprocessingGlobalOptimizer(
        objective_fn=lambda **kwargs: rosenbrock(**kwargs),
        parameter_config=parameter_config,
        optimizer_config={"optimizer": "CMA", "budget": 20, "num_workers": 1},
        execution_config={},
        event_system=event_system
    )
    
    # Start optimization in a separate thread
    import threading
    opt_thread = threading.Thread(target=optimizer.optimize)
    opt_thread.start()
    
    # Let it run for a few iterations
    import time
    time.sleep(1.0)
    
    # Pause optimization
    event_system.request_pause()
    iterations_at_pause = iterations_before_pause
    
    # Wait a bit
    time.sleep(0.5)
    
    # Resume optimization
    event_system.request_resume()
    
    # Wait for completion
    opt_thread.join()
    
    # Verify behavior
    assert iterations_at_pause < total_iterations
    assert total_iterations <= 20  # Should not exceed budget


def test_global_optimizer_skip_task():
    """Test task skipping functionality."""
    event_system = OptimizationEventSystem()
    iterations_completed = 0
    
    def count_iterations(data):
        nonlocal iterations_completed
        iterations_completed += 1
    
    event_system.subscribe("ITERATION_COMPLETE", count_iterations)
    
    # Configure optimizer
    parameter_config = {
        "x": {"type": "scalar", "init": 0.0, "lower": -2.0, "upper": 2.0},
        "y": {"type": "scalar", "init": 0.0, "lower": -2.0, "upper": 2.0},
    }
    
    optimizer = MultiprocessingGlobalOptimizer(
        objective_fn=lambda **kwargs: rosenbrock(**kwargs),
        parameter_config=parameter_config,
        optimizer_config={"optimizer": "CMA", "budget": 50, "num_workers": 1},
        execution_config={},
        event_system=event_system
    )
    
    # Start optimization in a separate thread
    import threading
    opt_thread = threading.Thread(target=optimizer.optimize)
    opt_thread.start()
    
    # Let it run for a few iterations
    import time
    time.sleep(1.0)
    
    # Skip current task
    event_system.request_skip()
    
    # Wait for completion
    opt_thread.join()
    
    # Verify behavior
    assert iterations_completed < 50  # Should have stopped before budget 