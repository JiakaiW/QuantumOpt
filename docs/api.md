# QuantumOpt API Documentation

## Overview

The QuantumOpt API provides endpoints for managing optimization tasks, monitoring their progress, and controlling their execution. The API is organized around REST principles and uses standard HTTP response codes. All responses are in JSON format.

## Base URL

```
http://localhost:8000/api/v1
```

## Authentication

Currently, the API does not require authentication. Future versions will implement authentication.

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
    "objective_fn": "def objective(param1):\n    return param1 ** 2"
}
```

The `objective_fn` field accepts a string containing a Python function definition. This design enables:
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
        "status": "pending",
        "config": {
            "name": "Example Optimization",
            "parameter_config": {...},
            "optimizer_config": {...},
            "execution_config": {...}
        }
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
        "config": {...},
        "result": {
            "best_params": {...},
            "best_value": 0.123,
            "iterations": 50,
            "total_evaluations": 75
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
        "status": "paused"
    }
}
```

## Queue Management

### Get Queue Status

Get the current status of the task queue.

```http
GET /queue/status
```

#### Response

```json
{
    "status": "success",
    "data": {
        "active_task_id": "550e8400-e29b-41d4-a716-446655440000",
        "task_count": 5,
        "is_processing": true,
        "is_paused": false
    }
}
```

### Control Queue

Control the queue's operation.

```http
POST /queue/control
```

#### Request Body

```json
{
    "action": "start"
}
```

#### Response

```json
{
    "status": "success",
    "data": {
        "active_task_id": "550e8400-e29b-41d4-a716-446655440000",
        "task_count": 5,
        "is_processing": true,
        "is_paused": false
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
        "type": "ITERATION_COMPLETED",
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
- `QUEUE_STARTED`: Queue processing started
- `QUEUE_STOPPED`: Queue processing stopped
- `QUEUE_PAUSED`: Queue processing paused
- `QUEUE_RESUMED`: Queue processing resumed

### Optimization Events
- `ITERATION_COMPLETED`: New optimization iteration
- `NEW_BEST_FOUND`: New best result found
- `OPTIMIZATION_COMPLETED`: Optimization finished
- `OPTIMIZATION_ERROR`: Error during optimization

### System Events
- `CONNECTED`: WebSocket connection established
- `RECONNECTED`: Client reconnected after disconnect
- `QUEUE_STATUS`: Queue status update
- `ERROR`: Error occurred during processing

## Usage Examples

### Creating and Monitoring a Task

1. Create a new task:
```python
import requests
import json

task_config = {
    "name": "Example Optimization",
    "parameter_config": {
        "x": {"lower_bound": -5.0, "upper_bound": 5.0, "scale": "linear"},
        "y": {"lower_bound": -5.0, "upper_bound": 5.0, "scale": "linear"}
    },
    "optimizer_config": {
        "optimizer_type": "CMA",
        "budget": 100,
        "num_workers": 4
    },
    "execution_config": {
        "max_retries": 3,
        "timeout": 3600
    },
    "objective_fn": "def objective(x, y): return x**2 + y**2"
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
    async with websockets.connect(
        "ws://localhost:8000/api/v1/ws",
        extra_headers={"Client-ID": "example-client"}
    ) as websocket:
        while True:
            message = await websocket.recv()
            event = json.loads(message)
            if event["data"]["type"] == "ITERATION_COMPLETED":
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

4. Control queue:
```python
# Start queue processing
requests.post("http://localhost:8000/api/v1/queue/control", json={"action": "start"})

# Pause queue
requests.post("http://localhost:8000/api/v1/queue/control", json={"action": "pause"})
```

## Task States

### Available States
Tasks can transition through the following states:

| State      | Description                                      |
|------------|--------------------------------------------------|
| pending    | Task is queued but not yet started               |
| running    | Task is currently executing                       |
| paused     | Task execution is temporarily suspended           |
| completed  | Task has finished successfully                    |
| failed     | Task encountered an error during execution        |
| stopped    | Task was manually stopped by user                 |

### State Transitions
```
pending → running → completed
    ↓        ↓         ↑
    ↓      paused      ↑
    ↓        ↓         ↑
    → → → stopped → → →|
         failed
```

### Task Status Response
```json
{
    "status": "success",
    "data": {
        "task_id": "123e4567-e89b-12d3-a456-426614174000",
        "status": "running",
        "name": "Example Task",
        "created_at": "2024-01-01T12:00:00Z",
        "result": null,
        "error": null
    }
}
``` 