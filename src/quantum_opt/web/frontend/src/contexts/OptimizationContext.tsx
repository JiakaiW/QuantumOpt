import { createContext, useContext, useReducer, useCallback, useEffect } from 'react';
import { useWebSocket } from '../hooks/useWebSocket';

export type TaskStatus = 'pending' | 'running' | 'paused' | 'completed' | 'failed';

export interface Task {
  task_id: string;
  status: 'pending' | 'running' | 'paused' | 'completed' | 'failed';
  result?: {
    optimization_trace: Array<{
      iteration: number;
      value: number;
      best_value: number;
      timestamp: string;
    }>;
    best_value?: number;
  };
  error?: string;
}

interface OptimizationState {
  tasks: Record<string, Task>;
  connected: boolean;
}

type UpdateAction = {
  type: 'UPDATE_TASK';
  payload: {
    task_id: string;
    updates: Partial<Task>;
  };
};

type SetTasksAction = {
  type: 'SET_TASKS';
  payload: Record<string, Task>;
};

type SetConnectedAction = {
  type: 'SET_CONNECTED';
  payload: boolean;
};

type AddTaskAction = {
  type: 'ADD_TASK';
  payload: {
    task_id: string;
    task: Task;
  };
};

type Action = UpdateAction | SetTasksAction | SetConnectedAction | AddTaskAction;

interface OptimizationContextType {
  state: OptimizationState;
  dispatch: React.Dispatch<Action>;
  startTask: (taskId: string) => void;
  pauseTask: (taskId: string) => void;
  resumeTask: (taskId: string) => void;
  stopTask: (taskId: string) => void;
}

const initialState: OptimizationState = {
  tasks: {},
  connected: false
};

function optimizationReducer(state: OptimizationState, action: Action): OptimizationState {
  switch (action.type) {
    case 'SET_CONNECTED':
      return { ...state, connected: action.payload };
    case 'ADD_TASK':
      console.log('Adding task:', action.payload);
      return {
        ...state,
        tasks: {
          ...state.tasks,
          [action.payload.task_id]: action.payload.task
        }
      };
    case 'UPDATE_TASK': {
      const currentTask = state.tasks[action.payload.task_id];
      if (!currentTask) return state;

      // Debug log for task update
      console.log('Updating task in reducer:', {
        task_id: action.payload.task_id,
        current_trace_length: currentTask.result?.optimization_trace?.length,
        new_trace_length: action.payload.updates.result?.optimization_trace?.length,
        status: action.payload.updates.status
      });

      // Create updated result with proper trace handling
      const updatedResult = action.payload.updates.result
        ? {
            ...currentTask.result,
            ...action.payload.updates.result,
            optimization_trace: action.payload.updates.result.optimization_trace || []
          }
        : currentTask.result;

      const updatedTask = {
        ...currentTask,
        ...action.payload.updates,
        result: updatedResult
      };

      // Debug log for final task state
      console.log('Task after update:', {
        task_id: action.payload.task_id,
        trace_length: updatedTask.result?.optimization_trace?.length,
        status: updatedTask.status,
        latest_value: updatedTask.result?.optimization_trace?.slice(-1)[0]?.value,
        latest_best: updatedTask.result?.optimization_trace?.slice(-1)[0]?.best_value
      });

      return {
        ...state,
        tasks: {
          ...state.tasks,
          [action.payload.task_id]: updatedTask
        }
      };
    }
    case 'SET_TASKS':
      return {
        ...state,
        tasks: action.payload
      };
    default:
      return state;
  }
}

const OptimizationContext = createContext<OptimizationContextType | null>(null);

export function OptimizationProvider({ children }: { children: React.ReactNode }) {
  const [state, dispatch] = useReducer(optimizationReducer, initialState);
  const { connected, sendMessage, lastMessage } = useWebSocket('/api/v1/ws');

  useEffect(() => {
    dispatch({ type: 'SET_CONNECTED', payload: connected });
  }, [connected]);

  // Fetch tasks when component mounts
  useEffect(() => {
    async function fetchTasks() {
      try {
        const response = await fetch('/api/v1/tasks');
        const data = await response.json();
        if (data.status === 'success') {
          // Convert tasks array to record if it's an array
          const tasksRecord: Record<string, Task> = {};
          if (Array.isArray(data.data)) {
            data.data.forEach((task: Task) => {
              tasksRecord[task.task_id] = task;
            });
          } else if (typeof data.data === 'object' && data.data !== null) {
            // If it's already a record, use it directly
            Object.assign(tasksRecord, data.data);
          }
          dispatch({ type: 'SET_TASKS', payload: tasksRecord });
        }
      } catch (error) {
        console.error('Error fetching tasks:', error);
      }
    }
    fetchTasks();
  }, []);

  // Handle WebSocket messages
  useEffect(() => {
    if (!lastMessage) return;

    try {
      const message = typeof lastMessage === 'string' ? JSON.parse(lastMessage) : lastMessage;
      
      if (message.data?.type === 'QUEUE_EVENT') {
        const { event_type, task_id, action, data } = message.data;

        switch (event_type) {
          case 'TASK_PROGRESS':
            if (data.result) {
              const currentTask = state.tasks[task_id];
              if (!currentTask) break;

              const currentTrace = currentTask.result?.optimization_trace || [];
              
              // Debug log for raw data
              console.log('Raw task progress data:', {
                taskId: task_id,
                data: data.result,
                currentTrace
              });

              // Backend sends: { best_value, best_params, iteration, total_iterations }
              // We need to transform this into our trace format
              const newTrace = {
                iteration: data.result.iteration,
                value: data.result.current_value || data.result.best_value, // Use current_value if available, fallback to best_value
                best_value: data.result.best_value,
                timestamp: new Date().toISOString(),
              };

              // Debug log for new trace point
              console.log('Adding trace point:', newTrace);

              const updatedTrace = [...currentTrace, newTrace];

              // Debug log for updated trace
              console.log('Updated trace:', {
                taskId: task_id,
                traceLength: updatedTrace.length,
                lastPoint: updatedTrace[updatedTrace.length - 1]
              });

              dispatch({
                type: 'UPDATE_TASK',
                payload: {
                  task_id,
                  updates: {
                    status: 'running',
                    result: {
                      optimization_trace: updatedTrace,
                      best_value: data.result.best_value
                    }
                  }
                }
              });
            }
            break;

          case 'TASK_CONTROL':
            const newStatus = action === 'start' ? 'running' 
              : action === 'pause' ? 'paused'
              : action === 'resume' ? 'running'
              : action === 'stop' ? 'completed'
              : undefined;

            if (newStatus) {
              dispatch({
                type: 'UPDATE_TASK',
                payload: {
                  task_id,
                  updates: {
                    status: newStatus
                  }
                }
              });
            }
            break;

          case 'TASK_ADDED':
            dispatch({
              type: 'ADD_TASK',
              payload: {
                task_id,
                task: {
                  task_id,
                  status: data.status || 'pending',
                  result: {
                    optimization_trace: [],
                    best_value: undefined
                  }
                }
              }
            });
            break;

          case 'TASK_FAILED':
            dispatch({
              type: 'UPDATE_TASK',
              payload: {
                task_id,
                updates: {
                  status: 'failed',
                  error: data.error
                }
              }
            });
            break;
        }
      }
    } catch (error) {
      console.error('Error processing WebSocket message:', error);
    }
  }, [lastMessage]);

  const controlTask = useCallback((taskId: string, action: string) => {
    sendMessage({
      type: 'CONTROL_TASK',
      data: {
        task_id: taskId,
        action
      }
    });
  }, [sendMessage]);

  const startTask = useCallback((taskId: string) => {
    controlTask(taskId, 'start');
  }, [controlTask]);

  const pauseTask = useCallback((taskId: string) => {
    controlTask(taskId, 'pause');
  }, [controlTask]);

  const resumeTask = useCallback((taskId: string) => {
    controlTask(taskId, 'resume');
  }, [controlTask]);

  const stopTask = useCallback((taskId: string) => {
    controlTask(taskId, 'stop');
  }, [controlTask]);

  const value = {
    state,
    dispatch,
    startTask,
    pauseTask,
    resumeTask,
    stopTask
  };

  return (
    <OptimizationContext.Provider value={value}>
      {children}
    </OptimizationContext.Provider>
  );
}

export function useOptimizationContext() {
  const context = useContext(OptimizationContext);
  if (!context) {
    throw new Error('useOptimizationContext must be used within an OptimizationProvider');
  }
  return context;
} 