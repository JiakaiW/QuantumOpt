# Quantum Optimization Web Examples

This directory contains example implementations of web interfaces for the Quantum Optimization package.

## Simple UI

The `simple-ui` directory contains a minimal HTML/JavaScript implementation that demonstrates:
- Basic task creation and control
- Real-time progress monitoring via WebSocket
- Simple visualization of optimization progress
- Event logging

### Features
- Single HTML file with embedded JavaScript
- No external dependencies
- Uses the same API endpoints as the main React frontend
- Real-time progress bar and parameter display
- Event log for debugging

### Usage
1. Start the backend server:
   ```bash
   python -m quantum_opt.web.run
   ```

2. Open `simple-ui/index.html` in a web browser
3. Use the buttons to:
   - Create a new optimization task
   - Start the optimization queue
   - Stop the optimization queue
4. Watch the progress in real-time

### Purpose
This simple implementation serves as:
- A testing tool for the backend API
- A reference implementation
- A minimal example for understanding the system
- A fallback UI when needed

## Main React Frontend

The main React/TypeScript frontend implementation is in the `frontend` directory. It provides:
- Full-featured user interface
- Rich visualization options
- Advanced task management
- Comprehensive state management

Both implementations use the same backend API, demonstrating the flexibility of the system. 