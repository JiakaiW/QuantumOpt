import React, { useState, useEffect, useCallback } from 'react';
import { Line } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
} from 'chart.js';

// Register ChartJS components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
);

// API configuration
const API_BASE = 'http://localhost:8000/api/v1';
const WS_URL = 'ws://localhost:8000/api/v1/ws';

// Task configuration
const TEST_TASK = {
  name: "quadratic_test",
  parameter_config: {
    x: {
      lower_bound: -5.0,
      upper_bound: 5.0,
      init: 0.0,
      scale: "linear"
    },
    y: {
      lower_bound: -5.0,
      upper_bound: 5.0,
      init: 0.0,
      scale: "linear"
    }
  },
  optimizer_config: {
    optimizer_type: "CMA",
    budget: 100,
    num_workers: 1
  },
  execution_config: {
    max_retries: 3,
    timeout: 60.0
  },
  objective_fn: `def objective(x: float, y: float) -> float:
    return x**2 + y**2`
};

const SimpleOptimization: React.FC = () => {
  // State
  const [taskId, setTaskId] = useState<string | null>(null);
  const [status, setStatus] = useState<string>('idle');
  const [ws, setWs] = useState<WebSocket | null>(null);
  const [iterations, setIterations] = useState<number[]>([]);
  const [values, setValues] = useState<number[]>([]);
  const [error, setError] = useState<string | null>(null);

  // Create WebSocket connection
  useEffect(() => {
    const socket = new WebSocket(`${WS_URL}?client_id=test-client`);
    
    socket.onopen = () => {
      console.log('WebSocket connected');
      setStatus('connected');
    };
    
    socket.onmessage = (event) => {
      const message = JSON.parse(event.data);
      if (message.status === 'success') {
        if (message.data.type === 'TASK_UPDATE') {
          if (message.data.event_type === 'ITERATION_COMPLETED') {
            setIterations(prev => [...prev, prev.length]);
            setValues(prev => [...prev, message.data.data.best_value]);
          }
        }
      } else {
        setError(message.error?.message || 'Unknown error');
      }
    };
    
    socket.onclose = () => {
      console.log('WebSocket disconnected');
      setStatus('disconnected');
    };
    
    setWs(socket);
    
    return () => {
      socket.close();
    };
  }, []);

  // Create task
  const createTask = async () => {
    try {
      const response = await fetch(`${API_BASE}/tasks`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(TEST_TASK),
      });
      
      const data = await response.json();
      if (data.status === 'success') {
        setTaskId(data.data.task_id);
        setStatus('task_created');
      } else {
        setError(data.error?.message || 'Failed to create task');
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create task');
    }
  };

  // Control task
  const controlTask = async (action: string) => {
    if (!taskId) return;
    
    try {
      const response = await fetch(`${API_BASE}/tasks/${taskId}/${action}`, {
        method: 'POST',
      });
      
      const data = await response.json();
      if (data.status === 'success') {
        setStatus(data.data.status);
      } else {
        setError(data.error?.message || `Failed to ${action} task`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : `Failed to ${action} task`);
    }
  };

  // Chart data
  const chartData = {
    labels: iterations,
    datasets: [
      {
        label: 'Best Value',
        data: values,
        borderColor: 'rgb(75, 192, 192)',
        tension: 0.1,
      },
    ],
  };

  return (
    <div className="simple-optimization">
      <h1>Simple Optimization Test</h1>
      
      <div className="status">
        <p>Status: {status}</p>
        {error && <p className="error">{error}</p>}
      </div>
      
      <div className="controls">
        {!taskId && (
          <button onClick={createTask}>Create Task</button>
        )}
        
        {taskId && status === 'task_created' && (
          <button onClick={() => controlTask('start')}>Start</button>
        )}
        
        {taskId && status === 'running' && (
          <>
            <button onClick={() => controlTask('pause')}>Pause</button>
            <button onClick={() => controlTask('stop')}>Stop</button>
          </>
        )}
        
        {taskId && status === 'paused' && (
          <button onClick={() => controlTask('resume')}>Resume</button>
        )}
      </div>
      
      {iterations.length > 0 && (
        <div className="chart">
          <h2>Optimization Progress</h2>
          <Line data={chartData} />
        </div>
      )}
    </div>
  );
};

export default SimpleOptimization; 