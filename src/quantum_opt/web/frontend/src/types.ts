export interface Task {
    id: string;
    status: 'pending' | 'running' | 'paused' | 'completed' | 'failed';
    progress: number;
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

export interface TaskConfig {
    name: string;
    parameter_config: {
        [key: string]: {
            lower_bound: number;
            upper_bound: number;
            init: number;
            scale: string;
        };
    };
    optimizer_config: {
        optimizer_type: string;
        budget: number;
        num_workers: number;
    };
    objective_fn: string;
}

export interface OptimizerConfig {
    optimizer_type: 'CMA' | 'OnePlusOne';
    budget: number;
    num_workers: number;
} 