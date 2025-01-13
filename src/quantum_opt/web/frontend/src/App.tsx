import React, { useEffect, useState } from 'react';
import { Container, Typography, Box, Paper } from '@mui/material';
import OptimizationPlot from './components/OptimizationPlot';

interface TaskData {
  iterations: number[];
  values: number[];
  bestValues: number[];
}

interface Task {
  task_id: string;
  name: string;
  status: string;
  source_code: string;
  result?: {
    error?: string;
    best_value?: number;
    best_params?: Record<string, number>;
  };
  data?: TaskData;
}

const App: React.FC = () => {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [ws, setWs] = useState<WebSocket | null>(null);

  useEffect(() => {
    // Connect to WebSocket
    const websocket = new WebSocket('ws://localhost:8000/api/ws/queue');
    setWs(websocket);

    websocket.onopen = () => {
      console.log('WebSocket Connected');
    };

    websocket.onmessage = (event) => {
      const message = JSON.parse(event.data);
      console.log('WebSocket message:', message);  // Debug log
      
      if (message.type === 'QUEUE_STATUS') {
        setTasks(message.data.tasks.map((task: any) => ({
          ...task,
          data: {
            iterations: [],
            values: [],
            bestValues: []
          }
        })));
      } else if (message.type === 'QUEUE_UPDATE') {
        const update = message.data;
        setTasks(prevTasks => {
          return prevTasks.map(task => {
            if (task.task_id === update.task_id) {
              // Initialize data if not exists
              const data = task.data || {
                iterations: [],
                values: [],
                bestValues: []
              };
              
              if (update.type === 'ITERATION_COMPLETE' && update.task.status === 'running') {
                const state = update.task.state;
                return {
                  ...task,
                  status: update.task.status,
                  data: {
                    iterations: [...data.iterations, state.iteration],
                    values: [...data.values, state.value],
                    bestValues: [...data.bestValues, state.best_value]
                  }
                };
              }
              
              return {
                ...update.task,
                data
              };
            }
            return task;
          });
        });
      }
    };

    websocket.onerror = (error) => {
      console.error('WebSocket error:', error);
    };

    return () => {
      websocket.close();
    };
  }, []);

  return (
    <Container maxWidth="lg">
      <Box sx={{ my: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          Quantum Optimization Tasks
        </Typography>
        
        {tasks.map(task => (
          <Paper key={task.task_id} sx={{ p: 3, mb: 4 }}>
            <Typography variant="h6" gutterBottom>
              {task.name} - Status: {task.status}
            </Typography>
            
            {/* Show error message if task failed */}
            {task.status === 'failed' && task.result?.error && (
              <Paper sx={{ p: 2, mb: 2, bgcolor: '#ffebee' }}>
                <Typography variant="subtitle1" color="error" gutterBottom>
                  Error:
                </Typography>
                <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                  {task.result.error}
                </pre>
              </Paper>
            )}

            {/* Show optimization result if completed */}
            {task.status === 'completed' && task.result && (
              <Paper sx={{ p: 2, mb: 2, bgcolor: '#e8f5e9' }}>
                <Typography variant="subtitle1" gutterBottom>
                  Best Value: {task.result.best_value}
                </Typography>
                <Typography variant="subtitle1" gutterBottom>
                  Best Parameters:
                </Typography>
                <pre>
                  {JSON.stringify(task.result.best_params, null, 2)}
                </pre>
              </Paper>
            )}

            {/* Show source code */}
            <Paper sx={{ p: 2, mb: 2, bgcolor: '#f5f5f5' }}>
              <Typography variant="subtitle1" gutterBottom>
                Source Code:
              </Typography>
              <pre style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
                {task.source_code}
              </pre>
            </Paper>

            {/* Show plot if we have data */}
            {task.data && (
              <OptimizationPlot
                taskId={task.task_id}
                data={task.data}
              />
            )}
          </Paper>
        ))}
      </Box>
    </Container>
  );
};

export default App; 