import React, { createContext, useContext, useReducer, useEffect } from 'react';
import { useWebSocket } from '../hooks/useWebSocket';

// Types
export interface Task {
    task_id: string;
    name: string;
    status: 'pending' | 'running' | 'completed' | 'failed';
    source_code: string;
    created_at: string;
    error?: string;
    result?: {
        best_value?: number;
        best_parameters?: Record<string, number>;
        total_evaluations?: number;
        optimization_time?: number;
        optimization_trace?: Array<{
            iteration: number;
            value: number;
            best_value: number;
            timestamp: string;
        }>;
    };
}

interface OptimizationState {
    tasks: Record<string, Task>;
    activeTaskId: string | null;
    connectionStatus: 'connected' | 'disconnected';
    error: string | null;
}

type OptimizationAction =
    | { type: 'SET_TASKS'; payload: Task[] }
    | { type: 'UPDATE_TASK'; payload: { taskId: string; updates: Partial<Task> } }
    | { type: 'SET_ACTIVE_TASK'; payload: string }
    | { type: 'SET_CONNECTION_STATUS'; payload: 'connected' | 'disconnected' }
    | { type: 'SET_ERROR'; payload: string | null }
    | { type: 'ADD_EVALUATION'; payload: { taskId: string; evaluation: any } };

// Context
const OptimizationContext = createContext<{
    state: OptimizationState;
    dispatch: React.Dispatch<OptimizationAction>;
} | null>(null);

// Initial state
const initialState: OptimizationState = {
    tasks: {},
    activeTaskId: null,
    connectionStatus: 'disconnected',
    error: null
};

// Reducer
function optimizationReducer(state: OptimizationState, action: OptimizationAction): OptimizationState {
    switch (action.type) {
        case 'SET_TASKS':
            return {
                ...state,
                tasks: action.payload.reduce((acc, task) => {
                    acc[task.task_id] = task;
                    return acc;
                }, {} as Record<string, Task>)
            };
            
        case 'UPDATE_TASK':
            return {
                ...state,
                tasks: {
                    ...state.tasks,
                    [action.payload.taskId]: {
                        ...state.tasks[action.payload.taskId],
                        ...action.payload.updates
                    }
                }
            };
            
        case 'SET_ACTIVE_TASK':
            return {
                ...state,
                activeTaskId: action.payload
            };
            
        case 'SET_CONNECTION_STATUS':
            return {
                ...state,
                connectionStatus: action.payload
            };
            
        case 'SET_ERROR':
            return {
                ...state,
                error: action.payload
            };
            
        case 'ADD_EVALUATION':
            const task = state.tasks[action.payload.taskId];
            if (!task) return state;
            
            const evaluation = action.payload.evaluation;
            const trace = task.result?.optimization_trace || [];
            
            return {
                ...state,
                tasks: {
                    ...state.tasks,
                    [action.payload.taskId]: {
                        ...task,
                        result: {
                            ...task.result,
                            optimization_trace: [...trace, {
                                iteration: evaluation.iteration,
                                value: evaluation.value,
                                best_value: evaluation.best_value,
                                timestamp: new Date().toISOString()
                            }]
                        }
                    }
                }
            };
            
        default:
            return state;
    }
}

// Provider component
export function OptimizationProvider({ children }: { children: React.ReactNode }) {
    const [state, dispatch] = useReducer(optimizationReducer, initialState);
    const { connected, lastMessage } = useWebSocket('ws://localhost:8000/api/ws/queue');
    
    // Handle connection status
    useEffect(() => {
        dispatch({ type: 'SET_CONNECTION_STATUS', payload: connected ? 'connected' : 'disconnected' });
    }, [connected]);
    
    // Handle WebSocket messages
    useEffect(() => {
        if (!lastMessage) return;
        
        try {
            const event = JSON.parse(lastMessage);
            
            switch (event.type) {
                case 'initial_state':
                case 'state_update':
                    if (event.tasks && Array.isArray(event.tasks)) {
                        dispatch({ type: 'SET_TASKS', payload: event.tasks });
                    }
                    break;
                    
                case 'task_evaluation':
                    dispatch({
                        type: 'ADD_EVALUATION',
                        payload: {
                            taskId: event.task_id,
                            evaluation: event.evaluation
                        }
                    });
                    break;
                    
                case 'error':
                    dispatch({ type: 'SET_ERROR', payload: event.error });
                    break;
                    
                default:
                    console.log('Unhandled event type:', event.type);
            }
        } catch (error) {
            console.error('Error processing WebSocket message:', error);
        }
    }, [lastMessage]);
    
    return (
        <OptimizationContext.Provider value={{ state, dispatch }}>
            {children}
        </OptimizationContext.Provider>
    );
}

// Hook for using the optimization context
export function useOptimization() {
    const context = useContext(OptimizationContext);
    if (!context) {
        throw new Error('useOptimization must be used within an OptimizationProvider');
    }
    return context;
} 