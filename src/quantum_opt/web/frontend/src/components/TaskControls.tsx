import { Button, ButtonGroup } from '@mui/material';
import { useOptimization } from '../contexts/OptimizationContext';

export const TaskControls: React.FC<{ task: Task }> = ({ task }) => {
  const { startTask, pauseTask, resumeTask, stopTask } = useOptimization();

  return (
    <ButtonGroup>
      {task.status === 'pending' && (
        <Button onClick={() => startTask(task.task_id)}>Start</Button>
      )}
      {task.status === 'running' && (
        <>
          <Button onClick={() => pauseTask(task.task_id)}>Pause</Button>
          <Button onClick={() => stopTask(task.task_id)}>Stop</Button>
        </>
      )}
      {task.status === 'paused' && (
        <>
          <Button onClick={() => resumeTask(task.task_id)}>Resume</Button>
          <Button onClick={() => stopTask(task.task_id)}>Stop</Button>
        </>
      )}
    </ButtonGroup>
  );
}; 