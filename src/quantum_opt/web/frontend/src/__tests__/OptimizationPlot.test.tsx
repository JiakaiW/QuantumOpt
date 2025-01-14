import { render, screen } from '@testing-library/react';
import { OptimizationPlot } from '../components/OptimizationPlot';

// Mock the Chart component
jest.mock('react-chartjs-2', () => ({
  Line: () => <div data-testid="mock-chart">Mock Chart</div>
}));

describe('OptimizationPlot', () => {
  const mockTask = {
    id: '123',
    task_id: '123',
    status: 'completed',
    result: {
      optimization_trace: [
        {
          iteration: 1,
          value: 0.5,
          best_value: 0.5,
          timestamp: '2024-01-01T00:00:00Z'
        },
        {
          iteration: 2,
          value: 0.3,
          best_value: 0.3,
          timestamp: '2024-01-01T00:00:01Z'
        }
      ]
    }
  };

  it('renders the chart with data', () => {
    render(<OptimizationPlot task={mockTask} />);
    expect(screen.getByTestId('mock-chart')).toBeInTheDocument();
  });

  it('renders with optimization trace data', () => {
    render(<OptimizationPlot task={mockTask} />);
    expect(screen.getByTestId('mock-chart')).toBeInTheDocument();
  });

  it('renders with empty optimization trace', () => {
    const emptyTask = {
      id: '456',
      task_id: '456',
      status: 'completed',
      result: {
        optimization_trace: []
      }
    };
    render(<OptimizationPlot task={emptyTask} />);
    expect(screen.getByTestId('mock-chart')).toBeInTheDocument();
  });
}); 