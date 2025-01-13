"""Tests for optimizer implementations."""
import pytest
import nevergrad as ng
from typing import Dict, Any
from quantum_opt.optimizers import MultiprocessingGlobalOptimizer
from quantum_opt.optimizers.base_optimizer import BaseParallelOptimizer
from quantum_opt.optimizers.optimization_schemas import OptimizationConfig, ParameterConfig, OptimizerConfig
from quantum_opt.utils.events import Event, EventType

def rosenbrock(x: float, y: float) -> float:
    """Rosenbrock function for testing optimization."""
    return (1 - x) ** 2 + 100 * (y - x ** 2) ** 2

@pytest.fixture
def optimizer_config() -> OptimizationConfig:
    """Create a test optimizer configuration."""
    return OptimizationConfig(
        name="test_optimization",
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
            budget=100,
            num_workers=1
        ),
        objective_fn=rosenbrock
    )

class TestBaseOptimizer:
    """Test suite for BaseParallelOptimizer."""
    
    class MockOptimizer(BaseParallelOptimizer):
        """Mock implementation of BaseParallelOptimizer for testing."""
        
        def _create_optimizer(self) -> ng.optimizers.base.Optimizer:
            """Create parameter instrumentation and optimizer."""
            # Create parameter space
            param_space = {}
            for name, param_config in self.config.parameter_config.items():
                param_space[name] = ng.p.Scalar(
                    init=param_config.init,
                    lower=param_config.lower_bound,
                    upper=param_config.upper_bound
                )
                
            # Create instrumentation
            instrumentation = ng.p.Instrumentation(**param_space)
            
            # Create optimizer
            return ng.optimizers.OnePlusOne(
                parametrization=instrumentation,
                budget=self.config.optimizer_config.budget,
                num_workers=self.config.optimizer_config.num_workers
            )
            
        async def _evaluate_candidate(self, candidate: Dict[str, Any]) -> float:
            """Mock evaluation that returns sum of squared parameters."""
            return self.config.objective_fn(**candidate)
    
    @pytest.mark.asyncio
    async def test_optimizer_initialization(self, optimizer_config: OptimizationConfig):
        """Test optimizer initialization."""
        optimizer = self.MockOptimizer(optimizer_config)
        assert optimizer.config == optimizer_config
        assert optimizer._stopped is False
        assert optimizer._optimizer is None
        assert optimizer._best_value == float('inf')
        assert optimizer._best_params is None
        
    @pytest.mark.asyncio
    async def test_optimization_basic_flow(self, optimizer_config: OptimizationConfig):
        """Test basic optimization flow."""
        optimizer = self.MockOptimizer(optimizer_config)
        events = []
        
        async def event_handler(event: Event):
            events.append(event)
            
        optimizer.add_subscriber(event_handler)
        result = await optimizer.optimize()
        
        assert isinstance(result, dict)
        assert "best_params" in result
        assert "best_value" in result
        assert "total_evaluations" in result
        assert result["total_evaluations"] <= optimizer_config.optimizer_config.budget
        assert len(events) > 0
        
    @pytest.mark.asyncio
    async def test_optimization_events(self, optimizer_config: OptimizationConfig):
        """Test event emission during optimization."""
        optimizer = self.MockOptimizer(optimizer_config)
        events = []
        
        async def event_handler(event: Event):
            events.append(event)
            
        optimizer.add_subscriber(event_handler)
        await optimizer.optimize()
        
        # Check for iteration completed events
        iteration_events = [e for e in events if e.type == EventType.ITERATION_COMPLETED]
        assert len(iteration_events) > 0
        
        # Verify event structure
        for event in iteration_events:
            assert "best_x" in event.data
            assert "best_y" in event.data
            assert isinstance(event.data["best_x"], dict)
            assert isinstance(event.data["best_y"], float)

class TestGlobalOptimizer:
    """Test suite for MultiprocessingGlobalOptimizer."""
    
    @pytest.mark.asyncio
    async def test_global_optimizer_creation(self, optimizer_config: OptimizationConfig):
        """Test global optimizer initialization."""
        optimizer = MultiprocessingGlobalOptimizer(optimizer_config)
        assert isinstance(optimizer, BaseParallelOptimizer)
        
    @pytest.mark.asyncio
    async def test_global_optimizer_log_scale(self, optimizer_config: OptimizationConfig):
        """Test optimizer with log-scale parameters."""
        # Update config to use log scale
        optimizer_config.parameter_config["x"].scale = "log"
        optimizer_config.parameter_config["x"].init = 1.0
        
        optimizer = MultiprocessingGlobalOptimizer(optimizer_config)
        result = await optimizer.optimize()
        
        assert isinstance(result, dict)
        assert result["best_value"] is not None
        assert isinstance(result["best_params"], dict)
        
    @pytest.mark.asyncio
    async def test_global_optimizer_cma(self, optimizer_config: OptimizationConfig):
        """Test optimizer with CMA strategy."""
        # Update config to use CMA
        optimizer_config.optimizer_config.optimizer_type = "CMA"
        optimizer_config.optimizer_config.num_workers = 4
        
        optimizer = MultiprocessingGlobalOptimizer(optimizer_config)
        result = await optimizer.optimize()
        
        assert isinstance(result, dict)
        assert result["best_value"] is not None
        assert isinstance(result["best_params"], dict)
        
    @pytest.mark.asyncio
    async def test_global_optimization_convergence(self, optimizer_config: OptimizationConfig):
        """Test optimization convergence to known minimum."""
        # Update config to use CMA with more budget
        optimizer_config.optimizer_config.optimizer_type = "CMA"
        optimizer_config.optimizer_config.budget = 200
        optimizer_config.optimizer_config.num_workers = 4
        
        # Set better initial points
        optimizer_config.parameter_config["x"].init = 0.5
        optimizer_config.parameter_config["y"].init = 0.5
        
        optimizer = MultiprocessingGlobalOptimizer(optimizer_config)
        result = await optimizer.optimize()
        
        # The Rosenbrock function has a global minimum at (1, 1)
        assert abs(result["best_params"]["x"] - 1.0) < 0.5
        assert abs(result["best_params"]["y"] - 1.0) < 0.5
        assert result["best_value"] < 1.0  # Should be close to 0 