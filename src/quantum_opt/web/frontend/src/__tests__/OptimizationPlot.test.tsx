import React from 'react';
import { render, screen } from '@testing-library/react';
import { OptimizationPlot } from '../components/OptimizationPlot';
import Chart from 'chart.js/auto';

// Mock Chart.js
jest.mock('chart.js/auto', () => {
    return jest.fn().mockImplementation(() => ({
        destroy: jest.fn(),
        update: jest.fn()
    }));
});

describe('OptimizationPlot', () => {
    const mockTaskId = 'test-task-123';
    const mockData = {
        best_value: 0.001,
        total_evaluations: 100,
        optimization_time: 10.5,
        optimization_trace: [
            {
                iteration: 0,
                value: 1.0,
                best_value: 1.0,
                timestamp: '2024-01-01T00:00:00Z'
            },
            {
                iteration: 1,
                value: 0.5,
                best_value: 0.5,
                timestamp: '2024-01-01T00:00:01Z'
            },
            {
                iteration: 2,
                value: 0.001,
                best_value: 0.001,
                timestamp: '2024-01-01T00:00:02Z'
            }
        ]
    };

    beforeEach(() => {
        jest.clearAllMocks();
    });

    it('renders plot with optimization data', () => {
        render(<OptimizationPlot taskId={mockTaskId} data={mockData} />);
        
        // Check if Chart.js was initialized
        expect(Chart).toHaveBeenCalled();
        
        // Check if statistics are displayed
        expect(screen.getByText('Best Value: 1.000e-3')).toBeInTheDocument();
        expect(screen.getByText('Evaluations: 100')).toBeInTheDocument();
        expect(screen.getByText('Time: 10.50s')).toBeInTheDocument();
    });

    it('handles empty optimization trace', () => {
        const emptyData = {
            ...mockData,
            optimization_trace: []
        };
        
        render(<OptimizationPlot taskId={mockTaskId} data={emptyData} />);
        expect(Chart).toHaveBeenCalled();
    });

    it('handles missing optimization data', () => {
        render(<OptimizationPlot taskId={mockTaskId} data={{}} />);
        expect(Chart).toHaveBeenCalled();
    });

    it('updates chart when data changes', () => {
        const { rerender } = render(
            <OptimizationPlot taskId={mockTaskId} data={mockData} />
        );

        const initialChartCalls = (Chart as jest.Mock).mock.calls.length;

        // Update with new data
        const newData = {
            ...mockData,
            optimization_trace: [
                ...mockData.optimization_trace,
                {
                    iteration: 3,
                    value: 0.0005,
                    best_value: 0.0005,
                    timestamp: '2024-01-01T00:00:03Z'
                }
            ]
        };

        rerender(<OptimizationPlot taskId={mockTaskId} data={newData} />);

        // Chart should not be recreated, only updated
        expect((Chart as jest.Mock).mock.calls.length).toBe(initialChartCalls);
    });

    it('cleans up chart on unmount', () => {
        const { unmount } = render(
            <OptimizationPlot taskId={mockTaskId} data={mockData} />
        );

        const mockChart = (Chart as jest.Mock).mock.instances[0];
        unmount();

        expect(mockChart.destroy).toHaveBeenCalled();
    });
}); 