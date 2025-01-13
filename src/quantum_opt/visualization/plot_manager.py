"""Plot manager for real-time visualization of optimization progress."""

from typing import Dict, List, Optional, Tuple
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.axes import Axes
from ..utils.events import OptimizationEvent, OptimizationState, OptimizationEventSystem

class OptimizationPlotManager:
    """Manager for real-time visualization of optimization progress."""
    
    def __init__(self, event_system: OptimizationEventSystem):
        """Initialize the plot manager.
        
        Args:
            event_system: Event system to subscribe to for updates
        """
        self._event_system = event_system
        self._iterations: List[int] = []
        self._values: List[float] = []
        self._best_values: List[float] = []
        
        # Create figure and axes
        self._fig, (self._ax1, self._ax2) = plt.subplots(2, 1, figsize=(10, 8))
        self._setup_plots()
        
        # Subscribe to events
        self._event_system.subscribe(
            OptimizationEvent.ITERATION_COMPLETE,
            self._on_iteration_complete
        )
        self._event_system.subscribe(
            OptimizationEvent.OPTIMIZATION_COMPLETE,
            self._on_optimization_complete
        )
        
    def _setup_plots(self) -> None:
        """Set up the plot layout and styling."""
        # Configure objective value plot
        self._ax1.set_title('Objective Value vs. Iteration')
        self._ax1.set_xlabel('Iteration')
        self._ax1.set_ylabel('Objective Value')
        self._ax1.grid(True)
        
        # Configure convergence plot
        self._ax2.set_title('Best Value vs. Iteration')
        self._ax2.set_xlabel('Iteration')
        self._ax2.set_ylabel('Best Value')
        self._ax2.grid(True)
        
        # Set up lines
        self._value_line, = self._ax1.plot([], [], 'b.', label='Current Value')
        self._best_line, = self._ax2.plot([], [], 'r-', label='Best Value')
        
        self._ax1.legend()
        self._ax2.legend()
        
        plt.tight_layout()
        
    def _on_iteration_complete(self, event: OptimizationEvent, state: OptimizationState, **kwargs) -> None:
        """Handle iteration complete event.
        
        Args:
            event: The event that occurred
            state: Current optimization state
            **kwargs: Additional event data
        """
        if 'value' in kwargs:
            self._iterations.append(state.iteration)
            self._values.append(kwargs['value'])
            self._best_values.append(state.best_value)
            
            self._update_plots()
            
    def _on_optimization_complete(self, event: OptimizationEvent, state: OptimizationState, **kwargs) -> None:
        """Handle optimization complete event.
        
        Args:
            event: The event that occurred
            state: Final optimization state
            **kwargs: Additional event data
        """
        self._update_plots(final=True)
        
    def _update_plots(self, final: bool = False) -> None:
        """Update the plots with current data.
        
        Args:
            final: Whether this is the final update
        """
        # Update objective value plot
        self._value_line.set_data(self._iterations, self._values)
        self._ax1.relim()
        self._ax1.autoscale_view()
        
        # Update convergence plot
        self._best_line.set_data(self._iterations, self._best_values)
        self._ax2.relim()
        self._ax2.autoscale_view()
        
        if final:
            self._ax1.set_title('Final Objective Values')
            self._ax2.set_title('Final Convergence Plot')
        
        plt.draw()
        plt.pause(0.01)  # Small pause to allow GUI to update
        
    @property
    def figure(self) -> Figure:
        """Get the matplotlib figure."""
        return self._fig 