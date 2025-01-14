import { Box, Paper, Typography, Divider, ListItem, ListItemText } from '@mui/material';
import { TaskControls } from './TaskControls';
import { OptimizationPlot } from './OptimizationPlot';
import { useOptimizationContext } from '../contexts/OptimizationContext';

export function TaskList() {
  const { state, startTask, pauseTask, resumeTask, stopTask } = useOptimizationContext();
  // Filter out any invalid tasks and ensure we have both taskId and valid task data
  const tasks = Object.entries(state.tasks).filter(([_, task]) => task && task.task_id);

  if (tasks.length === 0) {
    return (
      <Typography variant="body1" color="text.secondary" align="center" sx={{ mt: 4 }}>
        No tasks yet. Create a new task to get started.
      </Typography>
    );
  }

  return (
    <Box sx={{ mt: 4 }}>
      <Typography variant="h5" gutterBottom sx={{ mb: 3 }}>
        Optimization Tasks
      </Typography>
      
      {tasks.map((task) => (
        <ListItem key={task.task_id}>
          <ListItemText
            primary={`Task ${task.task_id}`}
            secondary={`Status: ${task.status}, Best Value: ${task.result?.best_value || 'N/A'}`}
          />
          <TaskControls task={task} />
        </ListItem>
      ))}
    </Box>
  );
} 