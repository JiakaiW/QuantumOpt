"""Example script to run the QuantumOpt web application with Rosenbrock function optimization."""
import sys
import webbrowser
import time
import asyncio
from pathlib import Path

# Add the src directory to the Python path if needed
src_dir = Path(__file__).parent.parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))

from quantum_opt.web.run import run_servers

if __name__ == "__main__":
    # Start the servers
    print("Starting QuantumOpt web application...")
    print("You can use this example configuration to test the optimization:")
    print("""
    {
        "parameter_config": {
            "x1": {
                "type": "float",
                "init": 0.0,
                "lower": -2.0,
                "upper": 2.0
            },
            "x2": {
                "type": "float",
                "init": 0.0,
                "lower": -2.0,
                "upper": 2.0
            }
        },
        "optimizer_config": {
            "optimizer": "CMA",
            "budget": 100,
            "num_workers": 4
        },
        "execution_config": {
            "checkpoint_dir": "./checkpoints",
            "log_file": "./logs/optimization.log",
            "log_level": "INFO",
            "precompile": true
        }
    }
    """)
    
    # Run the servers (this will handle opening the browser)
    run_servers(should_open_browser=True) 