import os
import sys
import functools

# Add path to CoupledQuantumSystems
repo_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.append(repo_root)

import numpy as np
import qutip
import pickle
from typing import Dict, Any
from CoupledQuantumSystems.drive import DriveTerm
from CoupledQuantumSystems.IFQ import gfIFQ
from CoupledQuantumSystems.evo import ODEsolve_and_post_process
from global_optimizer import MultiprocessingGlobalOptimizer

def create_quantum_system():
    """Create the quantum system."""
    EJ = 4
    EC = EJ/2
    EL = EJ/30
    
    qbt = gfIFQ(EJ=EJ, EC=EC, EL=EL, flux=0, truncated_dim=13)
    e_ops = [qutip.ket2dm(qutip.basis(qbt.truncated_dim, i)) for i in range(4)]
    initial_states = [qutip.basis(qbt.truncated_dim, 0), qutip.basis(qbt.truncated_dim, 2)]
    
    return qbt, e_ops, initial_states

def objective(detuning: float, t_duration: float, amp1_scaling_factor: float, amp2_scaling_factor: float) -> float:
    """Objective function for Raman gate optimization."""
    # Create quantum system inside the function
    qbt, e_ops, initial_states = create_quantum_system()
    
    detuning1 = detuning
    detuning2 = detuning
    tlist = np.linspace(0, t_duration, t_duration*2)
    
    drive_terms = qbt.get_Raman_DRAG_drive_terms(
        i=0,
        j=3,
        k=2,
        detuning1=detuning1,
        detuning2=detuning2,
        t_duration=t_duration,
        shape='sin^2',
        amp_scaling_factor=1,
        amp1_scaling_factor=amp1_scaling_factor,
        amp2_scaling_factor=amp2_scaling_factor,
        amp1_correction_scaling_factor=0,
        amp2_correction_scaling_factor=0,
    )
    
    results = []
    for init_state in initial_states:
        res = ODEsolve_and_post_process(
            y0=init_state,
            tlist=tlist,
            static_hamiltonian=qbt.diag_hamiltonian,
            drive_terms=drive_terms,
            e_ops=e_ops,
            print_progress=False,
        )
        results.append(res)
    
    one_minus_pop2 = np.abs(1 - (results[0].expect[2][-1] + 0.99 * results[0].expect[1][-1]))
    one_minus_pop0 = np.abs(1 - (results[1].expect[0][-1] + 0.99 * results[1].expect[1][-1]))
    return one_minus_pop2 + one_minus_pop0

def load_initial_results(filename: str = 'results_backup_four_level.pkl') -> Dict[str, Any]:
    """Load initial results from backup file."""
    if not os.path.exists(filename):
        raise FileNotFoundError(f"Initial results file {filename} not found")
    
    with open(filename, 'rb') as f:
        return pickle.load(f)

def evaluate_candidate(candidate, detuning, t_duration):
    """Evaluate a single candidate"""
    try:
        return objective(detuning=detuning, t_duration=t_duration, **candidate.kwargs)
    except Exception as e:
        print(f"Error evaluating candidate: {e}")
        return float('inf')

def objective_wrapper(x, detuning, t_duration):
    """Wrapper for the objective function to match optimizer's expected signature."""
    return evaluate_candidate(x, detuning, t_duration)

def optimize_raman_gate():
    """Main optimization function."""
    # Load initial results
    initial_results = load_initial_results()
    
    # Define parameter ranges
    detuning_arr = np.array([0.1, 0.2, 0.3, 0.4, 0.5])
    t_duration_arr = np.array([50, 100, 150, 200])
    
    # Configure optimizer
    parameter_config = {
        "amp1_scaling_factor": {
            "type": "log",
            "display_name": "Amp1",
            "format": ".6f",
            "width": 12,
            "style": "yellow"
        },
        "amp2_scaling_factor": {
            "type": "log",
            "display_name": "Amp2",
            "format": ".6f",
            "width": 12,
            "style": "magenta"
        }
    }
    
    optimizer_config = {
        "optimizer_type": "CMA",
        "budget": 200,
        "num_workers": 4
    }
    
    execution_config = {
        "checkpoint_dir": "./checkpoints/raman_gate",
        "log_file": "raman_gate_opt.log",
        "log_level": "INFO",
        "display_config": {
            "refresh_rate": 2,
            "show_time": True,
            "show_rate": True,
            "max_history": 20,
            "sort_by": "value"
        }
    }
    
    # Create results directory
    os.makedirs("./results", exist_ok=True)
    
    # Run optimization for each combination
    all_results = {}
    for detuning in detuning_arr:
        for t_duration in t_duration_arr:
            print(f"\nOptimizing for detuning={detuning}, t_duration={t_duration}")
            
            # Get initial values from backup
            amp1, amp2 = initial_results[(detuning, t_duration)]
            
            # Update parameter config with initial values
            parameter_config["amp1_scaling_factor"].update({
                "init": amp1,
                "lower": amp1/4,
                "upper": amp1*4
            })
            parameter_config["amp2_scaling_factor"].update({
                "init": amp2,
                "lower": amp2/4,
                "upper": amp2*4
            })
            
            # Create optimizer with wrapped objective function
            wrapped_objective = functools.partial(objective_wrapper, detuning=detuning, t_duration=t_duration)
            optimizer = MultiprocessingGlobalOptimizer(
                objective_fn=wrapped_objective,
                parameter_config=parameter_config,
                optimizer_config=optimizer_config,
                execution_config=execution_config
            )
            
            # Run optimization
            results = optimizer.optimize()
            
            # Store results
            all_results[(detuning, t_duration)] = {
                "detuning": float(detuning),
                "t_duration": float(t_duration),
                "best_amp1": float(results["best_params"]["amp1_scaling_factor"]),
                "best_amp2": float(results["best_params"]["amp2_scaling_factor"]),
                "best_value": float(results["best_value"]),
                "optimization_time": results["optimization_time"],
                "total_evaluations": results["total_evaluations"]
            }
            
            # Save results to file
            result_file = f"./results/raman_gate_opt_{detuning}_{t_duration}.pkl"
            with open(result_file, "wb") as f:
                pickle.dump(all_results[(detuning, t_duration)], f)
            
            print(f"Results saved to {result_file}")
            print(f"Best value: {results['best_value']:.6f}")
            print(f"Best parameters: amp1={results['best_params']['amp1_scaling_factor']:.6f}, "
                  f"amp2={results['best_params']['amp2_scaling_factor']:.6f}")
    
    return all_results

if __name__ == "__main__":
    # Create necessary directories
    os.makedirs("./checkpoints/raman_gate", exist_ok=True)
    
    # Run optimization
    print("Starting Raman gate optimization...")
    results = optimize_raman_gate()
    
    # Save final results
    with open("./results/raman_gate_final_results.pkl", "wb") as f:
        pickle.dump(results, f)
    print("\nOptimization complete. Final results saved to ./results/raman_gate_final_results.pkl") 