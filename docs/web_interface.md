# Web Interface Documentation

## Overview
The QuantumOpt web interface provides real-time visualization and control of multiple optimization tasks. It features a modern, responsive design built with React and Material-UI, offering both monitoring and control capabilities.

## Features

### Task Queue Visualization
- **Individual Task Cards**: Each optimization task is displayed in its own card, showing:
  - Task name and current status
  - Real-time optimization progress plot
  - Task-specific controls and information

### Real-Time Plotting
- **Live Progress Tracking**: Each task has its own Chart.js plot showing:
  - Current objective value (teal line)
  - Best objective value so far (red line)
  - Iteration count on x-axis
  - Automatic updates via WebSocket connection

### WebSocket Communication
- Real-time updates using WebSocket protocol
- Automatic reconnection on connection loss
- Event-based updates for:
  - Task status changes
  - Iteration completion
  - Optimization completion
  - Error reporting

### Task Management
- View multiple optimization tasks simultaneously
- Monitor task status:
  - Pending
  - Running
  - Completed
  - Failed
- Track optimization progress in real-time

## Usage Example

```python
from quantum_opt import OptimizationTask
from quantum_opt.web import run_servers

# Create multiple optimization tasks
tasks = [
    create_optimization_task(problem_id=1),
    create_optimization_task(problem_id=2),
    create_optimization_task(problem_id=3)
]

# Start the web interface
await run_servers(
    tasks=tasks,
    host="localhost",
    backend_port=8000,
    frontend_port=5173,
    should_open_browser=True
)
```

## Technical Details

### Frontend Stack
- React with TypeScript
- Material-UI for components
- Chart.js for real-time plotting
- WebSocket for live updates

### Backend Stack
- FastAPI for REST endpoints
- WebSocket support for real-time communication
- Async task processing
- Event-based architecture

### Data Flow
1. Backend processes optimization tasks
2. Updates sent via WebSocket to frontend
3. Frontend updates plots and status in real-time
4. Each task maintains its own state and visualization

## Development

### Running the Development Server
```bash
# Install frontend dependencies
cd src/quantum_opt/web/frontend
npm install

# Start the servers
python examples/queue_example.py
```

The web interface will be available at:
- Frontend & API: http://localhost:8000
- WebSocket: ws://localhost:8000/api/v1/ws

### Task States
Tasks can be in one of the following states:
- `pending`: Task is queued but not yet started
- `running`: Task is currently executing
- `paused`: Task execution is temporarily suspended
- `completed`: Task has finished successfully
- `failed`: Task encountered an error during execution
- `stopped`: Task was manually stopped by user

Each state transition triggers appropriate events that are broadcast to connected clients via WebSocket. 