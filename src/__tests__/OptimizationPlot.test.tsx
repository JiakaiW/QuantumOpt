import React from 'react';
import { render } from '@testing-library/react';
import '@testing-library/jest-dom';
import { OptimizationPlot } from '../components/OptimizationPlot';
import type { Task } from '../contexts/OptimizationContext';

describe('OptimizationPlot', () => {
  const mockTask: Task = {
    task_id: 'test-task-1',
    status: 'running',
    result: {
      optimization_trace: [
        {
          iteration: 1,
          value: 2.5,
          best_value: 2.5,
          timestamp: '2024-01-01T00:00:00Z'
        },
        {
          iteration: 2,
          value: 1.8,
          best_value: 1.8,
          timestamp: '2024-01-01T00:00:01Z'
        }
      ],
      best_value: 1.8
    }
  };

  const emptyTask: Task = {
    task_id: 'test-task-2',
    status: 'running',
    result: {
      optimization_trace: [],
      best_value: undefined
    }
  };

  it('renders the plot with data', () => {
    render(<OptimizationPlot task={mockTask} />);
    const canvas = document.querySelector('canvas');
    expect(canvas).toBeInTheDocument();
  });

  it('displays the best value', () => {
    render(<OptimizationPlot task={mockTask} />);
    const canvas = document.querySelector('canvas');
    expect(canvas).toBeInTheDocument();
  });

  it('handles empty optimization trace', () => {
    render(<OptimizationPlot task={emptyTask} />);
    const canvas = document.querySelector('canvas');
    expect(canvas).not.toBeInTheDocument();
  });
}); 