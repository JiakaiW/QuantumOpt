"""Tests for global optimizer implementation."""
import pytest
import numpy as np
import asyncio
from quantum_opt.optimizers import (
    MultiprocessingGlobalOptimizer,
    OptimizationConfig,
    ParameterConfig,
    OptimizerConfig
)
from quantum_opt.utils.events import Event, EventType

def rosenbrock(**kwargs):
    """Rosenbrock function for testing optimization."""
    x = kwargs.get('x', 0)
    y = kwargs.get('y', 0)
    return (1 - x) ** 2 + 100 * (y - x ** 2) ** 2

@pytest.fixture
def optimizer_config():
    """Create a test optimizer configuration."""
    return OptimizationConfig(
        name="test_basic",
        parameter_config={
            "x": ParameterConfig(
                lower_bound=-2.0,
                upper_bound=2.0,
                init=0.0,
                scale="linear"
            ),
            "y": ParameterConfig(
                lower_bound=-2.0,
                upper_bound=2.0,
                init=0.0,
                scale="linear"
            )
        },
        optimizer_config=OptimizerConfig(
            optimizer_type="OnePlusOne",
            budget=20,
            num_workers=1
        ),
        objective_fn=rosenbrock
    )

@pytest.mark.asyncio
@pytest.mark.timeout(5)
async def test_global_optimizer_basic(optimizer_config):
    """Test basic optimization functionality."""
    optimizer = MultiprocessingGlobalOptimizer(optimizer_config)
    try:
        result = await asyncio.wait_for(optimizer.optimize(), timeout=4)
        assert result is not None
        assert isinstance(result, dict)
        assert "best_params" in result
        assert "best_value" in result
        assert result["best_params"]["x"] > -2.0
        assert result["best_value"] < 1000.0
    except asyncio.TimeoutError:
        pytest.fail("Optimization timed out")

@pytest.mark.asyncio
async def test_global_optimizer_with_events(optimizer_config):
    """Test that events are emitted during optimization."""
    optimizer = MultiprocessingGlobalOptimizer(optimizer_config)
    events = []
    
    def event_handler(event: Event):
        events.append(event)
    
    optimizer.add_subscriber(event_handler)
    
    try:
        result = await asyncio.wait_for(optimizer.optimize(), timeout=4)
        assert result is not None
        assert len(events) > 0
        assert any(event.type == EventType.ITERATION_COMPLETED for event in events)
    except asyncio.TimeoutError:
        pytest.fail("Optimization timed out")

@pytest.mark.asyncio
@pytest.mark.timeout(5)
async def test_global_optimizer_error_handling(optimizer_config):
    """Test error handling during optimization."""
    def failing_objective(**kwargs):
        raise ValueError("Test error")
    
    config = optimizer_config.model_copy(update={
        "name": "test_error",
        "objective_fn": failing_objective,
        "optimizer_config": OptimizerConfig(
            optimizer_type="OnePlusOne",
            budget=5,  # Small budget for quick failure
            num_workers=1
        )
    })
    
    optimizer = MultiprocessingGlobalOptimizer(config)
    with pytest.raises(Exception) as exc_info:
        await optimizer.optimize()
    assert "Test error" in str(exc_info.value)

@pytest.mark.asyncio
async def test_global_optimizer_log_scale(optimizer_config):
    """Test optimization with log-scale parameters."""
    config = optimizer_config.model_copy(update={
        "name": "test_log_scale",
        "parameter_config": {
            "x": ParameterConfig(
                lower_bound=1e-3,
                upper_bound=1e3,
                init=1.0,
                scale="log"
            ),
            "y": ParameterConfig(
                lower_bound=1e-3,
                upper_bound=1e3,
                init=1.0,
                scale="log"
            )
        }
    })
    
    optimizer = MultiprocessingGlobalOptimizer(config)
    try:
        result = await asyncio.wait_for(optimizer.optimize(), timeout=4)
        assert result is not None
        assert isinstance(result, dict)
        assert "best_params" in result
        assert result["best_params"]["x"] > 0
        assert result["best_params"]["y"] > 0
    except asyncio.TimeoutError:
        pytest.fail("Optimization timed out") 