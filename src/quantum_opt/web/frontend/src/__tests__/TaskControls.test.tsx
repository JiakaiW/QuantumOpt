import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { TaskControls } from '../components/TaskControls';
import axios from 'axios';

jest.mock('axios');
const mockedAxios = axios as jest.Mocked<typeof axios>;

describe('TaskControls', () => {
    const mockTaskId = 'test-task-123';
    const mockOnError = jest.fn();

    beforeEach(() => {
        jest.clearAllMocks();
    });

    it('shows resume button when task is paused', () => {
        render(<TaskControls taskId={mockTaskId} status="paused" onError={mockOnError} />);
        expect(screen.getByText('Resume')).toBeInTheDocument();
    });

    it('shows pause button when task is running', () => {
        render(<TaskControls taskId={mockTaskId} status="running" onError={mockOnError} />);
        expect(screen.getByText('Pause')).toBeInTheDocument();
    });

    it('shows stop button when task is running or paused', () => {
        render(<TaskControls taskId={mockTaskId} status="running" onError={mockOnError} />);
        expect(screen.getByText('Stop')).toBeInTheDocument();

        render(<TaskControls taskId={mockTaskId} status="paused" onError={mockOnError} />);
        expect(screen.getByText('Stop')).toBeInTheDocument();
    });

    it('does not show any buttons for completed tasks', () => {
        render(<TaskControls taskId={mockTaskId} status="completed" onError={mockOnError} />);
        expect(screen.queryByRole('button')).not.toBeInTheDocument();
    });

    it('calls API and handles success when resuming task', async () => {
        mockedAxios.post.mockResolvedValueOnce({});
        
        render(<TaskControls taskId={mockTaskId} status="paused" onError={mockOnError} />);
        fireEvent.click(screen.getByText('Resume'));

        await waitFor(() => {
            expect(mockedAxios.post).toHaveBeenCalledWith(
                `http://localhost:8000/api/queue/task/${mockTaskId}/start`
            );
        });
        expect(mockOnError).not.toHaveBeenCalled();
    });

    it('calls API and handles success when pausing task', async () => {
        mockedAxios.post.mockResolvedValueOnce({});
        
        render(<TaskControls taskId={mockTaskId} status="running" onError={mockOnError} />);
        fireEvent.click(screen.getByText('Pause'));

        await waitFor(() => {
            expect(mockedAxios.post).toHaveBeenCalledWith(
                `http://localhost:8000/api/queue/task/${mockTaskId}/pause`
            );
        });
        expect(mockOnError).not.toHaveBeenCalled();
    });

    it('calls API and handles success when stopping task', async () => {
        mockedAxios.post.mockResolvedValueOnce({});
        
        render(<TaskControls taskId={mockTaskId} status="running" onError={mockOnError} />);
        fireEvent.click(screen.getByText('Stop'));

        await waitFor(() => {
            expect(mockedAxios.post).toHaveBeenCalledWith(
                `http://localhost:8000/api/queue/task/${mockTaskId}/stop`
            );
        });
        expect(mockOnError).not.toHaveBeenCalled();
    });

    it('handles API errors', async () => {
        const error = new Error('API Error');
        mockedAxios.post.mockRejectedValueOnce(error);
        
        render(<TaskControls taskId={mockTaskId} status="running" onError={mockOnError} />);
        fireEvent.click(screen.getByText('Stop'));

        await waitFor(() => {
            expect(mockOnError).toHaveBeenCalledWith(error.message);
        });
    });
}); 