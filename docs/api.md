# QuantumOpt API Documentation

## Overview
The QuantumOpt API provides endpoints for managing optimization tasks, controlling the task queue, and receiving real-time updates via WebSocket connections.

## Base URL
```
http://localhost:8000/api/v1
```

## Authentication
Currently, no authentication is required.

## Standard Response Format
All API endpoints return responses in a standardized format:

```json
{
  "status": "success" | "error",
  "data": { ... } | null,
  "error": { "message": "Error description" } | null
}
```

## Task Management

### Create Task
`POST /tasks`

Create a new optimization task.

**Request Body:**
```json
{
  "name": "string",
  "parameter_config": {
    "param_name": {
      "lower_bound": float,
      "upper_bound": float,
      "init": float | null,
      "scale": "linear" | "log"
    }
  },
  "optimizer_config": {
    "optimizer_type": "CMA" | "OnePlusOne",
    "budget": int,
    "num_workers": int
  },
  "execution_config": {
    "max_retries": int,
    "timeout": float
  },
  "objective_fn": "string"
}
```

- `name`: Name of the optimization task
- `parameter_config`: Dictionary mapping parameter names to their configurations
  - `lower_bound`: Lower bound for the parameter
  - `upper_bound`: Upper bound for the parameter
  - `init`: Optional initial value (defaults to middle of bounds)
  - `scale`: Scale type for the parameter ("linear" or "log")
- `optimizer_config`: Configuration for the optimizer
  - `optimizer_type`: Type of optimizer to use ("CMA" or "OnePlusOne")
  - `budget`: Number of function evaluations allowed
  - `num_workers`: Number of parallel workers (default: 1)
- `execution_config`: Optional configuration for task execution
  - `max_retries`: Maximum number of retries for failed evaluations (default: 3)
  - `timeout`: Timeout in seconds for the optimization (default: 3600.0)
- `objective_fn`: String representation of the objective function to optimize

**Response:**
```json
{
  "status": "success",
  "data": {
    "task_id": "string",
    "status": "pending"
  }
}
```

### Get Task
`GET /tasks/{task_id}`

Get the state of a specific task.

**Response:**
```json
{
  "status": "success",
  "data": {
    "task_id": "string",
    "status": "pending" | "running" | "paused" | "completed" | "failed" | "stopped",
    "config": { ... },
    "result": { ... } | null,
    "error": "string" | null
  }
}
```

### List Tasks
`GET /tasks`

Get a list of all tasks.

**Response:**
```json
{
  "status": "success",
  "data": {
    "tasks": [
      {
        "task_id": "string",
        "status": "string",
        "config": { ... },
        "result": { ... } | null,
        "error": "string" | null
      }
    ]
  }
}
```

### Control Task
The following endpoints control task execution:

#### Start Task
`POST /tasks/{task_id}/start`

Start or resume a task.

#### Pause Task
`POST /tasks/{task_id}/pause`

Pause a running task.

#### Resume Task
`POST /tasks/{task_id}/resume`

Resume a paused task.

#### Stop Task
`POST /tasks/{task_id}/stop`

Stop a task.

**Response (all control endpoints):**
```json
{
  "status": "success",
  "data": {
    "task_id": "string",
    "status": "string"
  }
}
```

## Queue Management

### Get Queue Status
`GET /queue/status`

Get the current status of the task queue.

**Response:**
```json
{
  "status": "success",
  "data": {
    "active_task_id": "string" | null,
    "task_count": int,
    "is_processing": boolean,
    "is_paused": boolean
  }
}
```

### Control Queue
`POST /queue/control`

Control the task queue's operation.

**Request Body:**
```json
{
  "action": "start" | "pause" | "resume" | "stop"
}
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "active_task_id": "string" | null,
    "task_count": int,
    "is_processing": boolean,
    "is_paused": boolean
  }
}
```

## Real-time Updates

### WebSocket Connection
`WS /ws?client_id={optional_client_id}`

Connect to receive real-time updates about tasks and queue status.

#### Message Format
All WebSocket messages follow this format:
```json
{
  "type": "string",
  "data": { ... }
}
```

#### Connection Flow
1. Client connects to WebSocket endpoint
2. Server sends connection confirmation:
```json
{
  "status": "success",
  "data": {
    "type": "CONNECTED",
    "client_id": "string"
  }
}
```

3. Server sends initial state:
```json
{
  "status": "success",
  "data": {
    "type": "INITIAL_STATE",
    "tasks": [ ... ]
  }
}
```

#### Client Messages

Request current state:
```json
{
  "type": "REQUEST_STATE",
  "data": {}
}
```

Control task:
```json
{
  "type": "CONTROL_TASK",
  "data": {
    "task_id": "string",
    "action": "start" | "pause" | "resume" | "stop"
  }
}
```

#### Server Events
The server sends events in the following format:
```json
{
  "status": "success",
  "data": {
    "type": "STATE_UPDATE" | "QUEUE_EVENT" | "TASK_UPDATE",
    "event_type": "string",
    "task_id": "string",
    "data": { ... }
  }
}
```

Event types include:
- Task lifecycle events: `TASK_CREATED`, `TASK_STARTED`, `TASK_COMPLETED`, etc.
- Optimization events: `ITERATION_COMPLETED`, `OPTIMIZATION_COMPLETED`
- Queue events: `QUEUE_STARTED`, `QUEUE_PAUSED`, etc.

## Error Handling
All endpoints return error responses in the following format:
```json
{
  "status": "error",
  "error": {
    "message": "Error description",
    "type": "ERROR_TYPE" | null
  }
}
```

Common HTTP status codes:
- 200: Success
- 400: Bad Request (invalid input)
- 404: Not Found (task or resource not found)
- 422: Unprocessable Entity (validation error)
- 500: Internal Server Error 