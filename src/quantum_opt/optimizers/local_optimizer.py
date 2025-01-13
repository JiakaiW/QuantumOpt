from typing import Dict, Any, Callable, List, Tuple
import os
import jax
import jax.numpy as jnp
import optax
from multiprocessing import Pool
import time
import numpy as np
from .base_optimizer import BaseParallelOptimizer

class MultiprocessingLocalOptimizer(BaseParallelOptimizer):
    """Implementation of parallel local optimization using gradient descent."""
    
    def __init__(self,
                 objective_fn: Callable,
                 gradient_fn: Callable,
                 parameter_config: Dict[str, Dict[str, Any]],
                 optimizer_config: Dict[str, Any],
                 execution_config: Dict[str, Any]):
        """Initialize local optimizer.
        
        Args:
            objective_fn: Function to optimize
            gradient_fn: Gradient function (e.g., from JAX)
            parameter_config: {
                "param_name": {
                    "values": List[float],     # Values to optimize for
                    "init_strategy": {         # How to initialize
                        "source": "file"|"value",
                        "pattern": str,        # File pattern or value
                        "transform": Callable  # Optional transform
                    },
                    "display_name": str,
                    "format": str,
                    "width": int,
                    "style": str
                }
            }
            optimizer_config: {
                "optimizer": str,           # Optax optimizer name
                "learning_rates": dict,     # Per-parameter learning rates
                "max_steps": int,          # Maximum optimization steps
                "num_workers": int,        # Number of parallel workers
                "early_stop_threshold": float,
                "early_stop_patience": int
            }
            execution_config: Same as BaseParallelOptimizer plus:
                "jax_config": dict         # JAX-specific configuration
        """
        super().__init__(objective_fn, parameter_config, optimizer_config, execution_config)
        self.gradient_fn = gradient_fn
        self.setup_jax_environment()
        self.parameter_combinations = self._generate_parameter_combinations()
    
    def setup_jax_environment(self):
        """Configure JAX environment."""
        jax_config = self.execution_config.get("jax_config", {})
        
        # Set environment variables
        os.environ['JAX_ENABLE_X64'] = str(jax_config.get('enable_x64', True)).lower()
        os.environ['XLA_PYTHON_CLIENT_MEM_FRACTION'] = str(jax_config.get('mem_fraction', 0.5))
        os.environ['XLA_PYTHON_CLIENT_PREALLOCATE'] = str(jax_config.get('preallocate', 'false')).lower()
        
        # Configure JAX
        if jax_config.get('enable_x64', True):
            jax.config.update('jax_enable_x64', True)
        
        # Set up compilation cache
        cache_dir = jax_config.get('cache_dir', './.jax_cache')
        if cache_dir:
            os.environ['JAX_COMPILATION_CACHE_DIR'] = os.path.abspath(cache_dir)
            os.makedirs(cache_dir, exist_ok=True)
            jax.config.update('jax_compilation_cache', True)
    
    def _generate_parameter_combinations(self) -> List[Dict[str, float]]:
        """Generate all parameter combinations to optimize."""
        combinations = []
        param_values = {}
        
        # Collect all parameter values
        for param_name, config in self.parameter_config.items():
            if "values" in config:
                param_values[param_name] = config["values"]
        
        # Generate combinations
        if not param_values:
            return [{}]
        
        # Get all combinations using numpy meshgrid
        param_names = list(param_values.keys())
        param_value_arrays = [param_values[name] for name in param_names]
        mesh = np.meshgrid(*param_value_arrays)
        
        # Convert to list of dictionaries
        for idx in np.ndindex(mesh[0].shape):
            combination = {
                name: mesh[i][idx]
                for i, name in enumerate(param_names)
            }
            combinations.append(combination)
        
        return combinations
    
    def _create_optimizer(self, learning_rates: Dict[str, float]) -> optax.GradientTransformation:
        """Create Optax optimizer with specified learning rates."""
        optimizer_name = self.optimizer_config.get("optimizer", "adam")
        optimizer_fn = getattr(optax, optimizer_name)
        
        return optimizer_fn(learning_rate=learning_rates)
    
    def _initialize_parameters(self, fixed_params: Dict[str, float]) -> Dict[str, float]:
        """Initialize parameters based on configuration."""
        params = {}
        for name, config in self.parameter_config.items():
            if name not in fixed_params and "init_strategy" in config:
                strategy = config["init_strategy"]
                if strategy["source"] == "file":
                    # Load from file using pattern
                    pattern = strategy["pattern"].format(**fixed_params)
                    if os.path.exists(pattern):
                        with open(pattern, 'rb') as f:
                            data = np.load(f)
                            value = data[name] if name in data else None
                    else:
                        value = None
                else:  # value
                    value = strategy["pattern"]
                
                if "transform" in strategy and value is not None:
                    value = strategy["transform"](value)
                
                if value is not None:
                    params[name] = value
        
        return params
    
    def init_worker(self):
        """Initialize worker process."""
        self._setup_logging()
        self._configure_environment()
        if self.execution_config.get("precompile", True):
            self._precompile_functions()
    
    def _precompile_functions(self):
        """Precompile JAX functions."""
        self.logger.info("Pre-compiling JAX functions...")
        # Create dummy inputs based on parameter config
        dummy_params = {
            name: 0.1 for name in self.parameter_config.keys()
        }
        try:
            _ = self.objective_fn(**dummy_params)
            _ = self.gradient_fn(**dummy_params)
            self.logger.info("JAX function pre-compilation complete")
        except Exception as e:
            self.logger.error(f"Error during pre-compilation: {e}")
    
    def _optimize_single(self, args: Tuple[Dict[str, float], Dict[str, Any]]) -> Dict[str, Any]:
        """Optimize for a single parameter combination."""
        fixed_params, opt_config = args
        
        # Initialize parameters
        params = self._initialize_parameters(fixed_params)
        params.update(fixed_params)
        
        # Create optimizer
        optimizer = self._create_optimizer(opt_config["learning_rates"])
        opt_state = optimizer.init(params)
        
        # Initialize tracking
        best_value = float('inf')
        best_params = None
        no_improvement_count = 0
        current_value = self.objective_fn(**params)
        
        # Optimization loop
        for step in range(opt_config["max_steps"]):
            try:
                # Compute gradients
                grads = self.gradient_fn(**params)
                
                # Update parameters
                updates, opt_state = optimizer.update(grads, opt_state)
                params = optax.apply_updates(params, updates)
                
                # Evaluate new parameters
                current_value = self.objective_fn(**params)
                
                # Update best values
                if current_value < best_value:
                    best_value = current_value
                    best_params = dict(params)
                    no_improvement_count = 0
                else:
                    no_improvement_count += 1
                
                # Early stopping
                if no_improvement_count >= opt_config["early_stop_patience"]:
                    break
                
            except Exception as e:
                self.logger.error(f"Error in optimization step: {e}")
                break
        
        return {
            "fixed_params": fixed_params,
            "best_value": best_value,
            "best_params": best_params,
            "steps": step + 1
        }
    
    def optimize(self) -> List[Dict[str, Any]]:
        """Run parallel optimization for all parameter combinations.
        
        Returns:
            List of dictionaries containing optimization results for each combination
        """
        num_workers = self.optimizer_config["num_workers"]
        opt_configs = [self.optimizer_config for _ in self.parameter_combinations]
        
        with self.progress_tracker.live_display() as live:
            with Pool(processes=num_workers, initializer=self.init_worker) as pool:
                # Create optimization arguments
                opt_args = list(zip(self.parameter_combinations, opt_configs))
                
                # Start optimization
                results = []
                running = pool.imap_unordered(self._optimize_single, opt_args)
                
                # Process results as they complete
                completed = 0
                total = len(opt_args)
                
                for result in running:
                    completed += 1
                    results.append(result)
                    
                    # Update progress
                    self.progress_tracker.update(
                        value=result["best_value"],
                        params=result["best_params"],
                        running_jobs=total - completed
                    )
                    live.update(self.progress_tracker.create_table())
                    
                    # Save checkpoint
                    if completed % 5 == 0:
                        self._save_checkpoint({
                            "completed": completed,
                            "results": results
                        }, "local_opt")
        
        # Sort results by fixed parameters for consistency
        results.sort(key=lambda x: str(x["fixed_params"]))
        return results 