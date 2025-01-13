# QuantumOpt Package Design

## Architecture Overview

QuantumOpt is a specialized framework for quantum optimal control optimization, providing parallel task execution and real-time visualization through a modern web interface. The framework enables queuing multiple optimization tasks, each targeting different quantum control objectives, while allowing real-time monitoring and control of the optimization process.

### 1. Core Components

#### Quantum Optimization Engine
- Parallel optimization using Nevergrad for quantum control problems
- Task queue management for multiple optimization objectives
- Support for various quantum systems and control parameters
- Individual log and result file management per task
- Task-specific checkpoint and recovery system

#### Task Queue Management
- Sequential execution of queued optimization tasks
- Individual task configuration and logging
- Task prioritization and scheduling
- Manual intervention capabilities (stop/pause/resume)
- Automatic progression to next task on completion/interruption

#### Web Interface
- FastAPI backend server with task queue monitoring
- React frontend application for visualization
- Real-time WebSocket updates for active task
- Task queue status display and control
- Individual task log viewing

#### Event System
- Asynchronous event handling for optimization updates
- Task state management and transitions
- WebSocket event broadcasting
- Supported events:
  - ITERATION_COMPLETE
  - OPTIMIZATION_COMPLETE
  - TASK_STARTED
  - TASK_STOPPED
  - TASK_QUEUED
  - ERROR

### 2. Directory Structure

```
src/quantum_opt/
├── optimizers/
│   ├── global_optimizer.py    # Parallel optimization implementation
│   └── quantum_objectives/    # Quantum control objective functions
│       ├── raman_gate.py
│       └── custom_objectives.py
├── queue/
│   ├── task_manager.py       # Task queue implementation
│   └── task_config.py        # Task configuration handling
├── utils/
│   ├── events.py            # Event system implementation
│   └── logging.py           # Task-specific logging
├── web/
│   ├── backend/
│   │   ├── main.py         # FastAPI server implementation
│   │   └── queue_api.py    # Task queue endpoints
│   ├── frontend/
│   │   ├── src/
│   │   │   ├── components/
│   │   │   │   ├── TaskQueue.tsx    # Queue management UI
│   │   │   │   ├── OptimizationPlot.tsx
│   │   │   │   └── ControlPanel.tsx
│   │   │   └── App.tsx
│   │   └── vite.config.ts
│   └── run.py
└── __init__.py
```

### 3. Key Features

#### Quantum Optimization
- Multiple quantum control objectives support
- Task-specific parameter configurations
- Individual result and log files per task
- Checkpoint and recovery mechanisms
- Progress tracking and state management

#### Task Queue Management
- Sequential task execution
- Individual task configuration
- Manual task control
- Automatic task progression
- Task status monitoring

#### Web Interface
- Task queue overview and control
- Real-time visualization of active task
- Individual task log access
- Configuration management per task
- Error handling and status display

### 4. API Design

#### Backend API
```python
# Task Queue Endpoints
@app.post("/api/queue/add")
async def add_task(task_config: TaskConfig)

@app.get("/api/queue/status")
async def get_queue_status()

@app.post("/api/queue/task/{task_id}/stop")
async def stop_task(task_id: str)

@app.post("/api/queue/task/{task_id}/pause")
async def pause_task(task_id: str)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket)
```

#### Task Configuration
```python
class TaskConfig(BaseModel):
    task_id: str
    objective: str  # e.g., 'raman_gate'
    parameter_config: Dict[str, ParameterConfig]
    optimizer_config: OptimizerConfig
    execution_config: ExecutionConfig
    
    class ExecutionConfig(BaseModel):
        checkpoint_dir: str
        log_file: str
        result_file: str
        log_level: str
        precompile: bool
```

### 5. Task Queue System

#### Queue Management
```python
class TaskQueue:
    def add_task(self, task: TaskConfig)
    def get_next_task(self) -> Optional[TaskConfig]
    def stop_current_task(self)
    def get_queue_status(self) -> List[TaskStatus]
```

#### Task Execution
```python
async def execute_task(task: TaskConfig):
    # Initialize optimization
    # Set up logging
    # Run optimization
    # Save results
    # Progress to next task
```

## Development Guidelines

### 1. Code Style
- Python: PEP 8 compliance
- TypeScript: ESLint + Prettier
- Comprehensive documentation
- Type annotations

### 2. Testing
- Quantum objective function tests
- Task queue management tests
- Individual task logging tests
- Queue state management tests

### 3. Deployment
- Development mode with hot reloading
- Production build process
- Environment configuration
- Task persistence and recovery
