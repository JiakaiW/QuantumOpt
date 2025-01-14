import { useReducer, useCallback, useEffect } from 'react';
import { useWebSocket } from './useWebSocket';

export type TaskStatus = 'pending' | 'running' | 'paused' | 'completed' | 'failed';

interface OptimizationTrace {
  iteration: number;
  value: number;
  best_value: number;
  timestamp: string;
}

interface Task {
  task_id: string;
  status: TaskStatus;
  result?: {
    optimization_trace: OptimizationTrace[];
    best_value?: number;
  };
  error?: string;
}

interface OptimizationState {
  tasks: Record<string, Task>;
  connected: boolean;
}

type Action =
  | { type: 'SET_CONNECTED'; payload: boolean }
  | { type: 'ADD_TASK'; payload: { task_id: string; task: Task } }
  | { type: 'UPDATE_TASK'; payload: { task_id: string; updates: Partial<Task> } }
  | { type: 'SET_TASKS'; payload: Record<string, Task> };

const initialState: OptimizationState = {
  tasks: {},
  connected: false
};

function optimizationReducer(state: OptimizationState, action: Action): OptimizationState {
  switch (action.type) {
    case 'SET_CONNECTED':
      return { ...state, connected: action.payload };
    case 'ADD_TASK':
      return {
        ...state,
        tasks: {
          ...state.tasks,
          [action.payload.task_id]: action.payload.task
        }
      };
    case 'UPDATE_TASK':
      return {
        ...state,
        tasks: {
          ...state.tasks,
          [action.payload.task_id]: {
            ...state.tasks[action.payload.task_id],
            ...action.payload.updates
          }
        }
      };
    case 'SET_TASKS':
      return {
        ...state,
        tasks: action.payload
      };
    default:
      return state;
  }
}

export function useOptimization() {
  const [state, dispatch] = useReducer(optimizationReducer, initialState);
  const { connected, sendMessage, lastMessage } = useWebSocket('/api/v1/ws');

  useEffect(() => {
    dispatch({ type: 'SET_CONNECTED', payload: connected });
  }, [connected]);

  const controlTask = useCallback((task_id: string, action: string) => {
    const message = {
      type: 'CONTROL_TASK',
      data: {
        task_id,
        action
      }
    };
    sendMessage(message);
  }, [sendMessage]);

  const startTask = useCallback((task_id: string) => {
    controlTask(task_id, 'start');
  }, [controlTask]);

  const pauseTask = useCallback((task_id: string) => {
    controlTask(task_id, 'pause');
  }, [controlTask]);

  const resumeTask = useCallback((task_id: string) => {
    controlTask(task_id, 'resume');
  }, [controlTask]);

  const stopTask = useCallback((task_id: string) => {
    controlTask(task_id, 'stop');
  }, [controlTask]);

  // Process WebSocket messages
  useEffect(() => {
    if (!lastMessage) return;

    try {
      const message = typeof lastMessage === 'string' ? JSON.parse(lastMessage) : lastMessage;
      
      if (message.status === 'success') {
        const { type, task_id, data } = message.data;

        switch (type) {
          case 'TASK_STARTED':
            dispatch({
              type: 'UPDATE_TASK',
              payload: {
                task_id,
                updates: { 
                  status: 'running',
                  result: {
                    optimization_trace: [],
                    best_value: undefined
                  }
                }
              }
            });
            break;

          case 'OPTIMIZATION_PROGRESS':
            if (!state.tasks[task_id]) break;
            
            const currentTrace = state.tasks[task_id]?.result?.optimization_trace || [];
            const newTrace = {
              iteration: data.iteration,
              value: data.value,
              best_value: data.best_value,
              timestamp: data.timestamp || new Date().toISOString(),
            };

            dispatch({
              type: 'UPDATE_TASK',
              payload: {
                task_id,
                updates: {
                  status: 'running',
                  result: {
                    optimization_trace: [...currentTrace, newTrace],
                    best_value: data.best_value
                  }
                }
              }
            });
            break;

          case 'OPTIMIZATION_COMPLETED':
            dispatch({
              type: 'UPDATE_TASK',
              payload: {
                task_id,
                updates: {
                  status: 'completed',
                  result: {
                    ...state.tasks[task_id]?.result,
                    best_value: data.best_value
                  }
                }
              }
            });
            break;

          case 'OPTIMIZATION_ERROR':
            dispatch({
              type: 'UPDATE_TASK',
              payload: {
                task_id,
                updates: {
                  status: 'failed',
                  error: data.error,
                }
              }
            });
            break;

          case 'TASK_PAUSED':
            dispatch({
              type: 'UPDATE_TASK',
              payload: {
                task_id,
                updates: { status: 'paused' }
              }
            });
            break;

          case 'TASK_RESUMED':
            dispatch({
              type: 'UPDATE_TASK',
              payload: {
                task_id,
                updates: { status: 'running' }
              }
            });
            break;

          case 'TASK_STOPPED':
            dispatch({
              type: 'UPDATE_TASK',
              payload: {
                task_id,
                updates: { status: 'completed' }
              }
            });
            break;
        }
      }
    } catch (error) {
      console.error('Error processing WebSocket message:', error);
    }
  }, [lastMessage, state.tasks]);

  const handleWebSocketMessage = (message: any) => {
    if (message.status === 'success') {
      switch (message.data.type) {
        case 'TASK_STARTED':
          dispatch({ type: 'UPDATE_TASK', payload: { task_id: message.data.task_id, status: 'running' } });
          break;
        case 'OPTIMIZATION_PROGRESS':
          dispatch({
            type: 'UPDATE_TASK',
            payload: {
              task_id: message.data.task_id,
              status: 'running',
              result: {
                optimization_trace: message.data.optimization_trace,
                best_value: message.data.best_value
              }
            }
          });
          break;
        case 'OPTIMIZATION_COMPLETED':
          dispatch({
            type: 'UPDATE_TASK',
            payload: {
              task_id: message.data.task_id,
              status: 'completed',
              result: {
                optimization_trace: message.data.optimization_trace,
                best_value: message.data.best_value
              }
            }
          });
          break;
        case 'OPTIMIZATION_ERROR':
          dispatch({
            type: 'UPDATE_TASK',
            payload: {
              task_id: message.data.task_id,
              status: 'failed',
              error: message.data.error
            }
          });
          break;
        case 'TASK_PAUSED':
          dispatch({ type: 'UPDATE_TASK', payload: { task_id: message.data.task_id, status: 'paused' } });
          break;
        case 'TASK_RESUMED':
          dispatch({ type: 'UPDATE_TASK', payload: { task_id: message.data.task_id, status: 'running' } });
          break;
        case 'TASK_STOPPED':
          dispatch({ type: 'UPDATE_TASK', payload: { task_id: message.data.task_id, status: 'completed' } });
          break;
      }
    }
  };

  return {
    state,
    dispatch,
    startTask,
    pauseTask,
    resumeTask,
    stopTask
  };
} 