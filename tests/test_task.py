"""Tests for task functionality."""
import asyncio
import pytest
from unittest.mock import Mock, patch, AsyncMock
from typing import Dict, Any, List
import json
import textwrap

from quantum_opt.queue.task import OptimizationTask
from quantum_opt.optimizers.optimization_schemas import OptimizationConfig, ParameterConfig, OptimizerConfig
from quantum_opt.utils.events import Event, EventType

@pytest.fixture
def optimization_config() -> OptimizationConfig:
    """Create a test optimization configuration."""
    parameter_config: Dict[str, ParameterConfig] = {
        "x": ParameterConfig(lower_bound=-2.0, upper_bound=2.0, scale="linear", init=0.0),
        "y": ParameterConfig(lower_bound=-2.0, upper_bound=2.0, scale="linear", init=0.0)
    }
    optimizer_config = OptimizerConfig(
        optimizer_type="CMA",
        budget=100,
        num_workers=1
    )
    objective_fn = "lambda x, y: (x - 1.0)**2 + (y - 1.0)**2"
    return OptimizationConfig(
        name="test_optimization",
        parameter_config=parameter_config,
        optimizer_config=optimizer_config,
        objective_fn=objective_fn,
        objective_fn_source=objective_fn
    )

@pytest.fixture
def optimization_config_str() -> str:
    """Create a test optimization configuration as a string."""
    config = {
        "name": "test_optimization",
        "parameter_config": {
            "x": {
                "lower_bound": -2.0,
                "upper_bound": 2.0,
                "scale": "linear",
                "init": 0.0
            },
            "y": {
                "lower_bound": -2.0,
                "upper_bound": 2.0,
                "scale": "linear",
                "init": 0.0
            }
        },
        "optimizer_config": {
            "optimizer_type": "CMA",
            "budget": 100,
            "num_workers": 1
        },
        "objective_fn": "lambda x, y: (x - 1.0)**2 + (y - 1.0)**2",
        "objective_fn_source": "lambda x, y: (x - 1.0)**2 + (y - 1.0)**2"
    }
    return json.dumps(config)

@pytest.fixture
def quantum_pulse_config_str() -> str:
    """Create a test configuration for quantum pulse optimization as a string."""
    # Define the objective function as a string that will be evaluated
    # This function creates a quantum system using QuTiP and optimizes pulse parameters
    objective_fn = textwrap.dedent("""
        def objective_fn(amplitude, frequency, duration, phase):
            import numpy as np
            import qutip as qt
            
            # System parameters
            N = 2  # Two-level system
            omega = 1.0  # Qubit frequency
            
            # Create operators
            sz = qt.sigmaz()
            sx = qt.sigmax()
            H0 = omega/2 * sz  # Static Hamiltonian
            
            # Time parameters
            nt = 100  # Number of time points
            times = np.linspace(0, duration, nt)
            
            # Create pulse envelope
            pulse = amplitude * np.sin(2*np.pi*frequency*times + phase)
            
            # Define time-dependent Hamiltonian terms
            H = [H0, [sx, lambda t, args: pulse[int(t/duration * (nt-1))]]]
            
            # Initial and target states
            psi0 = qt.basis([N], 0)  # Start in ground state
            target = (qt.basis([N], 0) + qt.basis([N], 1)).unit()  # Target is |+⟩ state
            
            # Solve Schrödinger equation
            result = qt.sesolve(H, psi0, times)
            
            # Calculate fidelity with target state at final time
            final_state = result.states[-1]
            fidelity = abs((target.dag() * final_state)[0,0])**2
            
            # Return negative fidelity (since we're minimizing)
            return -fidelity
    """)
    
    config = {
        "name": "quantum_pulse_optimization",
        "parameter_config": {
            "amplitude": {
                "lower_bound": 0.0,
                "upper_bound": 2.0,
                "scale": "linear",
                "init": 1.0
            },
            "frequency": {
                "lower_bound": 0.1,
                "upper_bound": 5.0,
                "scale": "log",
                "init": 1.0
            },
            "duration": {
                "lower_bound": 0.1,
                "upper_bound": 10.0,
                "scale": "log",
                "init": 1.0
            },
            "phase": {
                "lower_bound": 0.0,
                "upper_bound": 2*3.14159,
                "scale": "linear",
                "init": 0.0
            }
        },
        "optimizer_config": {
            "optimizer_type": "CMA",
            "budget": 200,
            "num_workers": 4
        },
        "objective_fn": objective_fn,
        "objective_fn_source": objective_fn
    }
    return json.dumps(config)

class TestOptimizationTask:
    """Test suite for OptimizationTask."""
    
    @pytest.mark.asyncio
    async def test_task_initialization(self, optimization_config: OptimizationConfig):
        """Test task initialization."""
        task = OptimizationTask(task_id="test_task", config=optimization_config)
        assert task.task_id == "test_task"
        assert task.status == "pending"
        assert task.result is not None
        assert task.result["optimization_trace"] == []
        assert task.result["best_value"] == float('inf')
        assert task.result["best_params"] is None
        assert task.error is None
        
    @pytest.mark.asyncio
    async def test_task_events(self, optimization_config: OptimizationConfig):
        """Test task event emission."""
        task = OptimizationTask(task_id="test_task", config=optimization_config)
        events: List[Event] = []
        
        async def event_handler(event: Event):
            events.append(event)
            
        task.add_subscriber(event_handler)
        
        # Create a mock optimizer that doesn't complete immediately
        mock_optimizer = AsyncMock()
        # Create an event to control optimization completion
        optimization_event = asyncio.Event()
        
        # Mock the optimize method to return a result after waiting
        async def mock_optimize():
            await optimization_event.wait()
            return {
                "best_value": 0.1,
                "best_params": {"x": 1.0, "y": 1.0},
                "total_evaluations": 10
            }
        mock_optimizer.optimize = AsyncMock(side_effect=mock_optimize)
        
        # Mock other methods
        mock_optimizer.cleanup = AsyncMock()  # Make cleanup async
        mock_optimizer.add_subscriber = Mock()  # Non-async add_subscriber
        mock_optimizer.pause = AsyncMock()
        mock_optimizer.resume = AsyncMock()
        
        with patch('quantum_opt.queue.task.MultiprocessingGlobalOptimizer', return_value=mock_optimizer):
            # Test start events
            start_task = asyncio.create_task(task.start())
            await asyncio.sleep(0.1)  # Allow task to start
            
            # Verify events
            event_types = [e.event_type for e in events]
            assert EventType.TASK_STARTED in event_types
            assert EventType.TASK_STATUS_CHANGED in event_types
            assert any(e.event_type == EventType.TASK_STATUS_CHANGED and 
                      e.data["new_status"] == "running" for e in events)
            
            # Test pause/resume
            await task.pause()
            assert task.status == "paused"
            mock_optimizer.pause.assert_awaited_once()
            
            await task.resume()
            assert task.status == "running"
            mock_optimizer.resume.assert_awaited_once()
            
            # Cleanup
            await task.stop()
            assert task.status == "stopped"
            mock_optimizer.cleanup.assert_awaited_once()
            
            # Set the event to allow the optimization task to complete
            optimization_event.set()
            await start_task
        
    @pytest.mark.asyncio
    async def test_task_state_transitions(self, optimization_config: OptimizationConfig):
        """Test task state transitions."""
        task = OptimizationTask(task_id="test_task", config=optimization_config)
        
        # Test initial state
        assert task.status == "pending"
        
        # Test start
        await task.start()
        assert task.status == "running"
        
        # Test pause
        await task.pause()
        assert task.status == "paused"
        
        # Test resume
        await task.resume()
        assert task.status == "running"
        
        # Test stop
        await task.stop()
        assert task.status == "stopped"
        
    @pytest.mark.asyncio
    async def test_optimization_process(self, optimization_config: OptimizationConfig):
        """Test the optimization process."""
        task = OptimizationTask(task_id="test_task", config=optimization_config)
        events: List[Event] = []
        
        async def event_handler(event: Event):
            events.append(event)
            
        task.add_subscriber(event_handler)
        
        # Create a mock optimizer
        mock_optimizer = AsyncMock()
        mock_optimizer.optimize = AsyncMock(return_value={
            "best_value": 0.1,
            "best_params": {"x": 1.0, "y": 1.0},
            "total_evaluations": 10
        })
        mock_optimizer.cleanup = AsyncMock()
        mock_optimizer.add_subscriber = Mock()
        
        with patch('quantum_opt.queue.task.MultiprocessingGlobalOptimizer', return_value=mock_optimizer):
            # Start optimization
            await task.start()
            
            # Wait for completion or timeout
            for _ in range(50):  # 5 second timeout
                if task.status == "completed":
                    break
                await asyncio.sleep(0.1)
                
            # Verify optimization completed successfully
            assert task.status == "completed"
            assert task.result is not None
            assert task.result["best_value"] < float('inf')
            assert task.result["best_params"] is not None
            assert len(task.result["optimization_trace"]) > 0
            assert task.result["total_evaluations"] > 0
            
            # Verify events
            event_types = [e.event_type for e in events]
            assert EventType.OPTIMIZATION_COMPLETED in event_types
            
    @pytest.mark.asyncio
    async def test_error_handling(self, optimization_config: OptimizationConfig):
        """Test error handling during optimization."""
        task = OptimizationTask(task_id="test_task", config=optimization_config)
        
        # Create a mock optimizer that raises an exception
        mock_optimizer = AsyncMock()
        mock_optimizer.optimize.side_effect = ValueError("Test error")
        mock_optimizer.cleanup = AsyncMock()
        
        with patch('quantum_opt.queue.task.MultiprocessingGlobalOptimizer', return_value=mock_optimizer):
            await task.start()
            
            # Wait for failure or timeout
            for _ in range(50):  # 5 second timeout
                if task.status == "failed":
                    break
                await asyncio.sleep(0.1)
            
            assert task.status == "failed"
            assert task.error == "Test error"
            
    @pytest.mark.asyncio
    async def test_cleanup_on_stop(self, optimization_config: OptimizationConfig):
        """Test resource cleanup when stopping task."""
        task = OptimizationTask(task_id="test_task", config=optimization_config)
        
        # Create a mock optimizer that doesn't complete immediately
        mock_optimizer = AsyncMock()
        optimization_event = asyncio.Event()
        
        # Mock the optimize method to return a result after waiting
        async def mock_optimize():
            await optimization_event.wait()
            return {
                "best_value": 0.1,
                "best_params": {"x": 1.0, "y": 1.0},
                "total_evaluations": 10
            }
        mock_optimizer.optimize = AsyncMock(side_effect=mock_optimize)
        mock_optimizer.cleanup = AsyncMock()
        mock_optimizer.add_subscriber = Mock()
        
        with patch('quantum_opt.queue.task.MultiprocessingGlobalOptimizer', return_value=mock_optimizer):
            # Start task
            start_task = asyncio.create_task(task.start())
            await asyncio.sleep(0.1)  # Allow task to start
            
            # Verify task is running
            assert task.status == "running"
            
            # Stop task
            await task.stop()
            assert task.status == "stopped"
            assert task._optimizer is None
            assert task.result["end_time"] is not None
            mock_optimizer.cleanup.assert_awaited_once()
            
            # Allow optimization task to complete
            optimization_event.set()
            await start_task
        
    @pytest.mark.asyncio
    async def test_task_initialization_with_string(self, optimization_config_str: str):
        """Test task initialization with string configuration."""
        task = OptimizationTask(task_id="test_task", config=optimization_config_str)
        
        # Verify task attributes
        assert task.task_id == "test_task"
        assert task.status == "pending"
        assert task.result is not None
        assert task.result["optimization_trace"] == []
        assert task.result["best_value"] == float('inf')
        assert task.result["best_params"] is None
        assert task.error is None
        
        # Verify config was parsed correctly
        assert isinstance(task.config, OptimizationConfig)
        assert task.config.name == "test_optimization"
        assert len(task.config.parameter_config) == 2
        assert "x" in task.config.parameter_config
        assert "y" in task.config.parameter_config
        assert task.config.optimizer_config.optimizer_type == "CMA"
        assert task.config.optimizer_config.budget == 100
        assert task.config.optimizer_config.num_workers == 1
        
        # Test starting the task
        await task.start()
        assert task.status == "running"
        
        # Clean up
        await task.stop()
        assert task.status == "stopped"
        
    @pytest.mark.asyncio
    async def test_quantum_pulse_optimization(self, quantum_pulse_config_str: str):
        """Test optimization of quantum control pulse parameters."""
        task = OptimizationTask(task_id="quantum_pulse_test", config=quantum_pulse_config_str)
        
        # Verify task initialization
        assert task.task_id == "quantum_pulse_test"
        assert task.status == "pending"
        assert isinstance(task.config, OptimizationConfig)
        
        # Verify parameter configuration
        param_config = task.config.parameter_config
        assert len(param_config) == 4
        assert all(param in param_config for param in ["amplitude", "frequency", "duration", "phase"])
        assert param_config["amplitude"].scale == "linear"
        assert param_config["frequency"].scale == "log"
        
        # Create a mock optimizer for testing
        mock_optimizer = AsyncMock()
        mock_optimizer.optimize = AsyncMock(return_value={
            "best_value": -0.99,  # High fidelity (remember we're minimizing negative fidelity)
            "best_params": {
                "amplitude": 1.2,
                "frequency": 0.8,
                "duration": 5.0,
                "phase": 0.0
            },
            "total_evaluations": 100
        })
        mock_optimizer.cleanup = AsyncMock()
        mock_optimizer.add_subscriber = Mock()
        
        events: List[Event] = []
        async def event_handler(event: Event):
            events.append(event)
        task.add_subscriber(event_handler)
        
        with patch('quantum_opt.queue.task.MultiprocessingGlobalOptimizer', return_value=mock_optimizer):
            # Start optimization
            await task.start()
            
            # Wait for completion or timeout
            for _ in range(50):  # 5 second timeout
                if task.status == "completed":
                    break
                await asyncio.sleep(0.1)
            
            # Verify optimization completed successfully
            assert task.status == "completed"
            assert task.result is not None
            assert task.result["best_value"] > -1.0  # Fidelity should be between 0 and 1
            assert task.result["best_params"] is not None
            assert len(task.result["optimization_trace"]) > 0
            
            # Verify we got reasonable pulse parameters
            best_params = task.result["best_params"]
            assert 0.0 <= best_params["amplitude"] <= 2.0
            assert 0.1 <= best_params["frequency"] <= 5.0
            assert 0.1 <= best_params["duration"] <= 10.0
            assert 0.0 <= best_params["phase"] <= 2*3.14159
            
            # Verify events
            event_types = [e.event_type for e in events]
            assert EventType.OPTIMIZATION_COMPLETED in event_types
            
            # Clean up
            await task.stop()
            assert task.status == "stopped"
        