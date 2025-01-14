import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { act } from 'react-dom/test-utils';
import SimpleOptimization from './SimpleOptimization';

// Mock WebSocket
class MockWebSocket {
  onopen: (() => void) | null = null;
  onmessage: ((event: any) => void) | null = null;
  onclose: (() => void) | null = null;
  close = jest.fn();
  send = jest.fn();

  constructor(url: string) {
    setTimeout(() => this.onopen?.(), 0);
  }
}

// Mock fetch
const mockFetch = jest.fn();

// Setup mocks
beforeEach(() => {
  global.WebSocket = MockWebSocket as any;
  global.fetch = mockFetch;
});

// Reset mocks
afterEach(() => {
  jest.resetAllMocks();
});

// Test configuration
const TEST_TIMEOUT = 5000; // 5 seconds timeout for tests

describe('SimpleOptimization', () => {
  // Add timeout to all tests
  jest.setTimeout(TEST_TIMEOUT);

  it('renders initial state correctly', () => {
    render(<SimpleOptimization />);
    
    expect(screen.getByText(/Simple Optimization Test/i)).toBeInTheDocument();
    expect(screen.getByText(/Status: idle/i)).toBeInTheDocument();
    expect(screen.getByText(/Create Task/i)).toBeInTheDocument();
  });

  it('establishes WebSocket connection', async () => {
    render(<SimpleOptimization />);
    
    await waitFor(() => {
      expect(screen.getByText(/Status: connected/i)).toBeInTheDocument();
    }, { timeout: TEST_TIMEOUT });
  });

  it('creates task successfully', async () => {
    const mockResponse = {
      status: 'success',
      data: {
        task_id: 'test-123',
        status: 'pending'
      }
    };

    mockFetch.mockResolvedValueOnce({
      json: async () => mockResponse
    });

    render(<SimpleOptimization />);
    
    const createButton = screen.getByText(/Create Task/i);
    await act(async () => {
      fireEvent.click(createButton);
    });

    await waitFor(() => {
      expect(screen.getByText(/Status: task_created/i)).toBeInTheDocument();
    }, { timeout: TEST_TIMEOUT });
  });

  it('handles task control actions', async () => {
    const mockCreateResponse = {
      status: 'success',
      data: {
        task_id: 'test-123',
        status: 'pending'
      }
    };

    const mockStartResponse = {
      status: 'success',
      data: {
        task_id: 'test-123',
        status: 'running'
      }
    };

    mockFetch
      .mockResolvedValueOnce({
        json: async () => mockCreateResponse
      })
      .mockResolvedValueOnce({
        json: async () => mockStartResponse
      });

    render(<SimpleOptimization />);
    
    // Create task
    const createButton = screen.getByText(/Create Task/i);
    await act(async () => {
      fireEvent.click(createButton);
    });

    // Start task
    const startButton = await screen.findByText(/Start/i, { timeout: TEST_TIMEOUT });
    await act(async () => {
      fireEvent.click(startButton);
    });

    await waitFor(() => {
      expect(screen.getByText(/Status: running/i)).toBeInTheDocument();
    }, { timeout: TEST_TIMEOUT });
  });

  it('displays optimization progress', async () => {
    const mockWs = new MockWebSocket('');
    render(<SimpleOptimization />);

    // Simulate iteration update
    await act(async () => {
      mockWs.onmessage?.({
        data: JSON.stringify({
          status: 'success',
          data: {
            type: 'TASK_UPDATE',
            event_type: 'ITERATION_COMPLETED',
            data: {
              best_value: 0.5
            }
          }
        })
      });
    });

    await waitFor(() => {
      expect(screen.getByText(/Optimization Progress/i)).toBeInTheDocument();
    }, { timeout: TEST_TIMEOUT });
  });

  it('handles errors gracefully', async () => {
    mockFetch.mockRejectedValueOnce(new Error('Network error'));

    render(<SimpleOptimization />);
    
    const createButton = screen.getByText(/Create Task/i);
    await act(async () => {
      fireEvent.click(createButton);
    });

    await waitFor(() => {
      expect(screen.getByText(/Network error/i)).toBeInTheDocument();
    }, { timeout: TEST_TIMEOUT });
  });
});

// Mock Chart.js to prevent errors
jest.mock('react-chartjs-2', () => ({
  Line: () => null
}));

jest.mock('chart.js', () => ({
  Chart: {
    register: jest.fn()
  },
  CategoryScale: jest.fn(),
  LinearScale: jest.fn(),
  PointElement: jest.fn(),
  LineElement: jest.fn(),
  Title: jest.fn(),
  Tooltip: jest.fn(),
  Legend: jest.fn()
})); 