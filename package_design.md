# QuantumOpt Package Design

## Architecture Overview

QuantumOpt is a general framework for optimization, providing parallel execution of objective functions and real-time visualization through a modern web interface. The framework enables queuing multiple optimization tasks, each targeting different quantum control objectives, while allowing real-time monitoring and control of the optimization process.

### Key Design Features

1. **String-Based Objective Functions**
   - Objective functions are defined as string-based Python function definitions
   - Enables frontend visualization of optimization objectives
   - Supports dynamic function creation and evaluation
   - Ensures safe serialization and storage
   - Allows arbitrary Python functions with proper validation

2. **Event-Driven Architecture**
   - Components communicate through typed events
   - Real-time updates via WebSocket
   - Standardized event formats

3. **Task Queue Management**
   - Sequential task processing
   - State machine-based task lifecycle
   - Pause/Resume/Stop capabilities

4. **Web Interface**
   - Modern React frontend
   - FastAPI backend
   - Real-time visualization

## Core Components and Implementation Status

### 1. Quantum Optimization Engine
**Implemented Features:**
- ✓ Parallel optimization using Nevergrad for global optimization
- ✓ Basic logging and result file management
- ✓ Event-based progress tracking
- ✓ Parameter configuration and validation

**Deferred Features:**
- ✗ JAX-based local optimization
- ✗ Task-specific checkpoint and recovery system

### 2. Task Queue Management
**Implemented Features:**
- ✓ Sequential execution of queued optimization tasks
- ✓ Individual task configuration and logging
- ✓ Manual intervention capabilities (stop/pause/resume)
- ✓ Automatic progression to next task
- ✓ Event-based communication
- ✓ Basic task state management

**Deferred Features:**
- ✗ Task persistence across restarts
- ✗ Task priority management
- ✗ Task dependency handling

### 3. Web Interface
**Implemented Features:**
- ✓ FastAPI backend with standardized API endpoints
- ✓ React frontend with real-time updates
- ✓ WebSocket-based communication
- ✓ Task queue monitoring and control
- ✓ Basic visualization with performance optimization
- ✓ Error handling and user feedback

**Deferred Features:**
- ✗ Task comparison view
- ✗ Advanced visualization options

### 4. Event System
**Implemented Features:**
- ✓ Unified event hierarchy
- ✓ Standardized event types and data structures
- ✓ WebSocket event broadcasting
- ✓ Basic event buffering
- ✓ Type-safe event handling

**Deferred Features:**
- ✗ Event persistence
- ✗ Event filtering
- ✗ Event replay capability

## Directory Structure and Component Relationships

```
src/quantum_opt/
├── optimizers/                 # Optimization algorithms
│   ├── global_optimizer.py     # Nevergrad-based parallel optimization
│   └── base_optimizer.py       # Abstract base class with event emission
├── queue/                      # Task management
│   ├── task.py                # Single task lifecycle management
│   └── manager.py             # Sequential task queue processing
├── utils/                      # Shared utilities
│   ├── events.py              # Unified event system
│   └── logging.py             # Logging utilities
└── web/                       # Web interface
    ├── backend/               # FastAPI backend
    │   ├── api/              # REST API endpoints
    │   │   └── v1/          # API version 1
    │   └── websocket_manager.py  # WebSocket handling
    └── frontend/             # React frontend
        └── src/
            ├── components/   # React components
            ├── contexts/     # State management
            └── hooks/       # Custom hooks
```

## Standard Formats and Protocols

For detailed API specifications, message formats, and examples, please refer to `docs/api.md`. Below is a high-level overview of the core protocols:

### 1. Task State Machine
```
pending → running → completed/failed/stopped
         ↑      ↓
         ← paused
```

### 2. Component Communication
- **Event-Based**: Components communicate through typed events
- **Async Operations**: All long-running operations are asynchronous
- **Error Handling**: Standardized error propagation through events
- **Real-time Updates**: WebSocket-based live updates to frontend

See `docs/api.md` for:
- Detailed API endpoints and usage
- Configuration formats and validation
- Event message structures and types
- WebSocket communication protocol
- Error handling and status codes

## Testing Strategy

### Unit Tests (Minimum 90% coverage)
1. **Core Components**
   - Optimizer implementations
   - Task and TaskQueue classes
   - Event system
   - Configuration validation

2. **API Layer**
   - REST endpoints
   - WebSocket communication
   - Request/response validation

3. **Frontend Components**
   - React components
   - State management
   - WebSocket integration

### Integration Tests
- Task lifecycle testing
- Event propagation
- Frontend-backend communication

## Development Guidelines
- Follow PEP 8 for Python and ESLint/Prettier for TypeScript
- Maintain comprehensive docstrings and type hints
- Implement proper error handling at all levels
- Use async/await for asynchronous operations
- Follow component-based architecture in frontend 

## Security Considerations

### Objective Function Execution
The framework executes user-provided objective functions as Python code. To ensure security:

1. **Sandboxing**
   - Functions are executed in a restricted environment
   - Limited access to Python builtins
   - No file system or network access
   - Timeout limits on execution

2. **Input Validation**
   - Function string must be valid Python code
   - Parameters must match configuration
   - Return value must be numeric
   - Size limits on function definition

3. **Resource Management**
   - Memory usage limits
   - CPU time constraints
   - Maximum iterations cap
   - Worker process isolation 