# QuantumOpt

High performance optimization framework for quantum optimal control with web visualization.

## Features

- Parallel optimization with multiple backends (Nevergrad, CMA-ES)
- Real-time visualization through web interface
- Event-driven architecture
- Modern, responsive UI
- Support for multiple optimization strategies

## Installation

### Python Package

The package is named `quantum_opt` (following Python packaging conventions) while the project is called QuantumOpt.

```bash
# Install the Python package
pip install quantum_opt

# For development
pip install quantum_opt[dev]
```

### Web Application Dependencies

The web interface requires Node.js (>=16) and npm. After installing these, set up the frontend:

```bash
# Navigate to frontend directory
cd src/quantum_opt/web/frontend

# Install dependencies
npm install

# If you see any warnings about deprecated packages, you can run:
npm audit fix
```

Required Python packages for the web interface (automatically installed with the package):
- FastAPI
- Uvicorn
- WebSockets
- Pydantic

## Usage

### Running the Web Interface

```python
from quantum_opt.web import run

if __name__ == "__main__":
    run.run_servers()
```

This will:
1. Start the FastAPI backend server
2. Launch the Vite development server
3. Open your browser to the application

### Using the Python API

```python
from quantum_opt.optimizers import MultiprocessingGlobalOptimizer

# Configure optimization
optimizer = MultiprocessingGlobalOptimizer(
    objective_fn=your_function,
    parameter_config={
        'param1': {'type': 'scalar', 'init': 0.0, 'lower': -1.0, 'upper': 1.0},
    },
    optimizer_config={
        'optimizer': 'CMA',
        'budget': 1000,
        'num_workers': 4
    }
)

# Run optimization
result = optimizer.optimize()
```

## Development

### Setup Development Environment

```bash
# Clone the repository
git clone https://github.com/yourusername/QuantumOpt.git
cd QuantumOpt

# Install Python development dependencies
pip install -e ".[dev]"

# Install and build frontend
cd src/quantum_opt/web/frontend
npm install
npm run build
```

### Running Tests

```bash
# Run Python tests
pytest

# Run frontend development server
cd src/quantum_opt/web/frontend
npm start

# Build frontend for production
npm run build
```

### Troubleshooting

If you see npm warnings during installation:
1. These are mostly about optional dependencies and don't affect functionality
2. You can try `npm audit fix` to automatically fix issues
3. We use specific versions of packages known to work together
4. The application will work correctly despite these warnings

## License

MIT License
