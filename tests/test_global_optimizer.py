"""Tests and examples for global optimizer implementation."""
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

def quadratic(x: float, y: float) -> float:
    """Simple quadratic function with known minimum at (1, 1).
    
    This function is of the form: f(x, y) = (x - 1)^2 + (y - 1)^2
    The global minimum is at (1, 1) with f(1, 1) = 0
    
    Args:
        x: First parameter
        y: Second parameter
        
    Returns:
        float: Function value
    """
    return (x - 1.0)**2 + (y - 1.0)**2

@pytest.fixture
def optimizer_config():
    """Create a test optimizer configuration."""
    config = OptimizationConfig(
        name="quadratic_optimization",
        parameter_config={
            "x": ParameterConfig(
                lower_bound=-5.0,
                upper_bound=5.0,
                init=0.0,
                scale="linear"
            ),
            "y": ParameterConfig(
                lower_bound=-5.0,
                upper_bound=5.0,
                init=0.0,
                scale="linear"
            )
        },
        optimizer_config=OptimizerConfig(
            optimizer_type="CMA",  # Using CMA for better convergence
            budget=100,  # Increased budget for better results
            num_workers=4  # Using parallel workers
        ),
        objective_fn=quadratic,
        objective_fn_source="""def quadratic(x: float, y: float) -> float:
    \"\"\"Simple quadratic function with known minimum at (1, 1).\"\"\"
    return (x - 1.0)**2 + (y - 1.0)**2"""
    )
    return config

@pytest.mark.asyncio
async def test_quadratic_optimization(optimizer_config):
    """Demonstrate optimization of a simple quadratic function."""
    # Create optimizer
    optimizer = MultiprocessingGlobalOptimizer(optimizer_config)
    
    # Track optimization progress
    progress = []
    async def event_handler(event: Event):
        if event.type == EventType.ITERATION_COMPLETED:
            progress.append({
                'iteration': len(progress),
                'value': event.data.get('best_y'),
                'x': event.data.get('best_x', {}).get('x'),
                'y': event.data.get('best_x', {}).get('y')
            })
    
    optimizer.add_subscriber(event_handler)
    
    # Run optimization
    try:
        result = await asyncio.wait_for(optimizer.optimize(), timeout=10)
        
        # Verify results
        assert result is not None
        assert isinstance(result, dict)
        assert "best_params" in result
        assert "best_value" in result
        
        # Check convergence to known minimum
        best_x = result["best_params"]["x"]
        best_y = result["best_params"]["y"]
        best_value = result["best_value"]
        
        print("\nOptimization Results:")
        print(f"Best parameters: x = {best_x:.6f}, y = {best_y:.6f}")
        print(f"Best value: {best_value:.6f}")
        print(f"Distance from true minimum: {((best_x-1)**2 + (best_y-1)**2)**0.5:.6f}")
        print(f"Number of iterations: {len(progress)}")
        
        # Print optimization progress
        print("\nOptimization Progress:")
        for i, p in enumerate(progress[::len(progress)//5]):  # Print ~5 points
            print(f"Iteration {p['iteration']}: "
                  f"f({p['x']:.3f}, {p['y']:.3f}) = {p['value']:.6f}")
        
        # Assert convergence
        assert abs(best_x - 1.0) < 0.1, "x did not converge to minimum"
        assert abs(best_y - 1.0) < 0.1, "y did not converge to minimum"
        assert best_value < 0.01, "function value did not reach minimum"
        
    except asyncio.TimeoutError:
        pytest.fail("Optimization timed out")

if __name__ == "__main__":
    # Allow running this file directly for demonstration
    pytest.main([__file__, "-v"]) 