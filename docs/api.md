# QuantumOpt API Documentation

## Overview

The QuantumOpt API provides endpoints for managing optimization tasks, monitoring their progress, and controlling their execution. The API is organized around REST principles and uses standard HTTP response codes. All responses are in JSON format.

## Base URL

```
http://localhost:8000/api/v1
```

## Authentication

Currently, the API does not require authentication.

## Task Management

### Create Task

Create a new optimization task.

```http
POST /tasks
```

#### Request Body

```json
{
    "name": "Example Optimization",
    "parameter_config": {
        "param1": {
            "lower_bound": 0.0,
            "upper_bound": 1.0,
            "init": 0.5,
            "scale": "linear"
        }
    },
    "optimizer_config": {
        "optimizer_type": "OnePlusOne",
        "budget": 100,
        "num_workers": 1
    },
    "execution_config": {
        "max_retries": 3,
        "timeout": 3600
    },
    "objective_fn": "def objective(param1):\n    # This is the function to minimize\n    return param1 ** 2"
}
```

The `objective_fn` field accepts a string containing a Python function definition. This design choice enables:
- Frontend display of the optimization objective
- Dynamic function creation without security risks
- Easy serialization and storage
- Support for arbitrary Python functions

Requirements for the objective function:
1. Must be a valid Python function definition
2. Function name must match the string after "def " and before "("
3. Parameters must match the keys in parameter_config
4. Must return a float value to minimize
5. Can use standard Python math operations and functions

Example objective functions:
```python
# Simple quadratic
def objective(x):
    return x ** 2

# Multi-parameter optimization
def objective(x, y, z):
    return x**2 + y**2 + z**2

# With mathematical functions
def objective(theta, phi):
    import math
    return math.sin(theta)**2 + math.cos(phi)**2
```

#### Response

```json
{
    "status": "success",
    "data": {
        "task_id": "550e8400-e29b-41d4-a716-446655440000",
        "status": "pending"
    }
}
```

### Get Task Status

Retrieve the status of a specific task.

```http
GET /tasks/{task_id}
```

#### Response

```json
{
    "status": "success",
    "data": {
        "task_id": "550e8400-e29b-41d4-a716-446655440000",
        "status": "running",
        "config": {
            "parameter_config": {...},
            "optimizer_config": {...},
            "execution_config": {...}
        },
        "result": {
            "best_params": {...},
            "best_value": 0.123,
            "iterations": 50
        }
    }
}
```

### List Tasks

Retrieve all tasks.

```http
GET /tasks
```

#### Response

```json
{
    "status": "success",
    "data": {
        "tasks": [
            {
                "task_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "running",
                "config": {...},
                "result": {...}
            }
        ]
    }
}
```

### Control Task

Control task execution with pause, resume, or stop operations.

```http
POST /tasks/{task_id}/pause
POST /tasks/{task_id}/resume
POST /tasks/{task_id}/stop
```

#### Response

```json
{
    "status": "success",
    "data": {
        "task_id": "550e8400-e29b-41d4-a716-446655440000",
        "status": "paused"  // or "running", "stopped"
    }
}
```

## Real-time Updates

### WebSocket Connection

Connect to receive real-time updates about tasks.

```
WebSocket: /api/v1/ws
```

Optional query parameter:
- `client_id`: For reconnection support

#### Connection Message

```json
{
    "status": "success",
    "data": {
        "type": "CONNECTED",
        "client_id": "client-123"
    }
}
```

#### Event Messages

Task Added:
```json
{
    "status": "success",
    "data": {
        "type": "TASK_ADDED",
        "task_id": "550e8400-e29b-41d4-a716-446655440000",
        "data": {
            "status": "pending",
            "config": {...}
        }
    }
}
```

Optimization Update:
```json
{
    "status": "success",
    "data": {
        "type": "ITERATION_COMPLETE",
        "task_id": "550e8400-e29b-41d4-a716-446655440000",
        "data": {
            "iteration": 10,
            "current_value": 0.5,
            "best_value": 0.1,
            "parameters": {...}
        }
    }
}
```

## Error Responses

The API uses standard HTTP status codes and provides detailed error messages:

```json
{
    "status": "error",
    "error": {
        "message": "Task not found",
        "details": "No task exists with ID: 550e8400-e29b-41d4-a716-446655440000"
    }
}
```

Common error codes:
- 400: Bad Request (invalid parameters)
- 404: Not Found (task doesn't exist)
- 409: Conflict (invalid state transition)
- 500: Internal Server Error

## Event Types

The following event types are emitted through WebSocket:

### Queue Events
- `TASK_ADDED`: New task added to queue
- `TASK_STARTED`: Task execution started
- `TASK_COMPLETED`: Task finished successfully
- `TASK_FAILED`: Task failed with error
- `TASK_STOPPED`: Task stopped by user

### Optimization Events
- `ITERATION_COMPLETE`: New optimization iteration
- `NEW_BEST_FOUND`: New best result found
- `OPTIMIZATION_COMPLETE`: Optimization finished

### System Events
- `CONNECTED`: WebSocket connection established
- `QUEUE_STATUS`: Queue status update
- `ERROR`: Error occurred during processing

## Configuration Objects

### Parameter Configuration
```json
{
    "param_name": {
        "lower_bound": number,
        "upper_bound": number
    }
}
```

### Optimizer Configuration
```json
{
    "optimizer_type": "nevergrad",
    "budget": number,  // Total number of evaluations
    "options": {...}   // Optional optimizer-specific settings
}
```

### Execution Configuration
```json
{
    "max_retries": number,  // Maximum retry attempts
    "timeout": number       // Timeout in seconds
}
```

## Usage Examples

### Creating and Monitoring a Task

1. Create a new task:
```python
import requests
import json

task_config = {
    "parameter_config": {
        "x": {"lower_bound": -5.0, "upper_bound": 5.0},
        "y": {"lower_bound": -5.0, "upper_bound": 5.0}
    },
    "optimizer_config": {
        "optimizer_type": "nevergrad",
        "budget": 100
    },
    "execution_config": {
        "max_retries": 3,
        "timeout": 3600
    },
    "objective_function": "def objective(params): return params['x']**2 + params['y']**2"
}

response = requests.post(
    "http://localhost:8000/api/v1/tasks",
    json=task_config
)
task_id = response.json()["data"]["task_id"]
```

2. Monitor progress via WebSocket:
```python
import websockets
import asyncio

async def monitor_task():
    async with websockets.connect("ws://localhost:8000/api/v1/ws") as websocket:
        while True:
            message = await websocket.recv()
            event = json.loads(message)
            if event["data"]["type"] == "ITERATION_COMPLETE":
                print(f"Iteration {event['data']['data']['iteration']}: "
                      f"Best value = {event['data']['data']['best_value']}")

asyncio.get_event_loop().run_until_complete(monitor_task())
```

3. Control task execution:
```python
# Pause task
requests.post(f"http://localhost:8000/api/v1/tasks/{task_id}/pause")

# Resume task
requests.post(f"http://localhost:8000/api/v1/tasks/{task_id}/resume")

# Stop task
requests.post(f"http://localhost:8000/api/v1/tasks/{task_id}/stop")
``` 