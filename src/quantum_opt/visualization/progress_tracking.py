from typing import Optional, Dict, Any
from rich.live import Live
from rich.table import Table
from rich.console import Console
from rich import box
import time

class OptimizationProgressTracker:
    def __init__(self, 
                 title: str,
                 parameter_config: Dict[str, Dict[str, Any]],
                 budget: int,
                 display_config: Optional[Dict[str, Any]] = None):
        """Initialize the progress tracker.
        
        Args:
            title: Title for the progress table
            parameter_config: Dict defining parameters to track
                {
                    "param_name": {
                        "display_name": str,  # Column header
                        "format": str,        # e.g. ".6f"
                        "width": int,         # Column width
                        "style": str          # Rich style
                    }
                }
            budget: Total optimization budget
            display_config: Optional display configuration
                {
                    "refresh_rate": float,    # Updates per second
                    "show_time": bool,        # Show elapsed time
                    "show_rate": bool,        # Show iterations/second
                    "max_history": int,       # Max evaluations to show
                    "sort_by": str           # Column to sort by
                }
        """
        self.title = title
        self.parameter_config = parameter_config
        self.total_budget = budget
        self.display_config = display_config or {
            "refresh_rate": 2,
            "show_time": True,
            "show_rate": True,
            "max_history": 20,
            "sort_by": "value"
        }
        
        # Initialize tracking variables
        self.start_time = time.time()
        self.best_value = float('inf')
        self.best_params = None
        self.current_budget = budget
        self.running_jobs = 0
        self.current_evaluations = []
        self.total_evaluations = 0
        
        # Set up console
        self.console = Console()
        
    def create_table(self) -> Table:
        """Create and return the progress table."""
        table = Table(title=self.title, box=box.ROUNDED)
        
        # Add status columns
        if self.display_config["show_time"]:
            table.add_column("Time", justify="right", style="cyan", width=8)
        table.add_column("Budget", justify="right", style="cyan", width=8)
        table.add_column("Jobs", justify="right", style="cyan", width=6)
        if self.display_config["show_rate"]:
            table.add_column("s/iter", justify="right", style="cyan", width=8)
        table.add_column("Best", justify="right", style="green", width=10)
        
        # Add parameter columns for best result
        for param_name, config in self.parameter_config.items():
            table.add_column(
                f"Best {config['display_name']}", 
                justify="right",
                style=config["style"],
                width=config["width"]
            )
        
        # Add current evaluation columns
        for param_name, config in self.parameter_config.items():
            table.add_column(
                config["display_name"],
                justify="right",
                style="magenta",
                width=config["width"]
            )
        table.add_column("Cost", justify="right", style="red", width=10)
        
        # Add rows
        self._add_status_row(table)
        self._add_evaluation_rows(table)
        
        return table
    
    def _add_status_row(self, table: Table):
        """Add the status row to the table."""
        elapsed = time.time() - self.start_time
        s_per_iter = "-"
        if self.total_evaluations > 0:
            s_per_iter = f"{elapsed/self.total_evaluations:.1f}"
        
        row = []
        if self.display_config["show_time"]:
            row.append(f"{elapsed:.1f}s")
        row.extend([
            str(self.current_budget),
            str(self.running_jobs)
        ])
        if self.display_config["show_rate"]:
            row.append(s_per_iter)
        row.append(f"{self.best_value:.6f}")
        
        # Add best parameters
        if self.best_params:
            for param_name, config in self.parameter_config.items():
                fmt = config.get("format", ".6f")
                row.append(f"{self.best_params[param_name]:{fmt}}")
        else:
            row.extend(["-"] * len(self.parameter_config))
        
        # Add empty cells for current evaluation columns
        row.extend(["-"] * (len(self.parameter_config) + 1))
        
        table.add_row(*row)
    
    def _add_evaluation_rows(self, table: Table):
        """Add rows for current evaluations."""
        if not self.current_evaluations:
            return
            
        # Sort evaluations if needed
        sorted_evals = sorted(
            self.current_evaluations,
            key=lambda x: x[1] if self.display_config["sort_by"] == "value" else x[0][self.display_config["sort_by"]]
        )
        
        # Limit number of shown evaluations
        sorted_evals = sorted_evals[:self.display_config["max_history"]]
        
        for params, value in sorted_evals:
            # Add empty cells for status columns
            row = []
            if self.display_config["show_time"]:
                row.append("-")
            row.extend(["-", "-"])
            if self.display_config["show_rate"]:
                row.append("-")
            row.append("-")
            
            # Add empty cells for best parameters
            row.extend(["-"] * len(self.parameter_config))
            
            # Add current evaluation
            for param_name, config in self.parameter_config.items():
                fmt = config.get("format", ".6f")
                row.append(f"{params[param_name]:{fmt}}")
            row.append(f"{value:.6f}")
            
            table.add_row(*row)
    
    def update(self, value: Optional[float] = None, params: Optional[dict] = None,
               budget: Optional[int] = None, running_jobs: Optional[int] = None):
        """Update the progress tracker with new information."""
        if value is not None and value < self.best_value:
            self.best_value = value
            self.best_params = params
        if budget is not None:
            self.current_budget = budget
        if running_jobs is not None:
            self.running_jobs = running_jobs
        if params is not None and value is not None:
            self.current_evaluations.append((params, value))
            self.total_evaluations += 1
            # Keep only recent evaluations
            if len(self.current_evaluations) > self.display_config["max_history"]:
                self.current_evaluations = self.current_evaluations[-self.display_config["max_history"]:]
    
    def live_display(self) -> Live:
        """Create and return a Live display context manager."""
        return Live(
            self.create_table(),
            refresh_per_second=self.display_config["refresh_rate"],
            console=self.console
        ) 