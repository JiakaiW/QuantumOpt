import asyncio
import json
import re
import textwrap

from quantum_opt.queue.task import OptimizationTask
from quantum_opt.optimizers.optimization_schemas import ParameterConfig, OptimizerConfig

# Create a module-level function that we can reference
objective_fn_code = """
import numpy as np
import qutip as qt

def objective_fn(amplitude=1.0, frequency=1.0, duration=1.0, phase=0.0):
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
    def pulse_coeff(t, args):
        # Ensure time index is within bounds
        idx = min(int(t/duration * (nt-1)), nt-1)
        return pulse[idx]
    
    H = [H0, [sx, pulse_coeff]]
    
    # Initial and target states
    psi0 = qt.basis([N], 0)  # Start in ground state
    target = (qt.basis([N], 0) + qt.basis([N], 1)).unit()  # Target is |+⟩ state
    
    # Solve Schrödinger equation
    result = qt.sesolve(H, psi0, times)
    
    # Calculate fidelity with target state at final time
    final_state = result.states[-1]
    fidelity = abs(target.overlap(final_state))**2
    
    # Return negative fidelity (since we're minimizing)
    return -fidelity
"""

async def main():
    # Create optimization configuration
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
        "objective_fn": "objective_fn",  # Reference the function by name
        "objective_fn_source": objective_fn_code  # Provide the source code
    }
    
    # Create and run optimization task
    task = OptimizationTask(task_id="quantum_pulse_test", config=json.dumps(config))
    
    # Subscribe to events
    async def event_handler(event):
        try:
            if event.event_type.name == "OPTIMIZATION_PROGRESS":
                if event.data.get('best_value') is not None:
                    print(f"Iteration {event.data['iteration']}: Best fidelity = {-event.data['best_value']:.4f}")
            elif event.event_type.name == "OPTIMIZATION_COMPLETED":
                if event.data.get('best_value') is not None:
                    print("\nOptimization completed!")
                    print(f"Best fidelity: {-event.data['best_value']:.4f}")
                    print("Best parameters:")
                    for param, value in event.data['best_params'].items():
                        print(f"  {param}: {value:.4f}")
        except Exception as e:
            print(f"Error in event handler: {e}")
    
    task.add_subscriber(event_handler)
    
    # Start optimization
    print("Starting optimization...")
    await task.start()
    
    # Wait for completion
    while task.status not in ["completed", "failed", "stopped"]:
        await asyncio.sleep(0.1)
    
    if task.status == "failed":
        print(f"Optimization failed: {task.error}")
    elif task.status == "completed":
        print("\nFinal optimization trace:")
        for point in task.result["optimization_trace"][-5:]:  # Show last 5 points
            if point.get('value') is not None:
                print(f"Iteration {point['iteration']}: Fidelity = {-point['value']:.4f}")

if __name__ == "__main__":
    asyncio.run(main()) 