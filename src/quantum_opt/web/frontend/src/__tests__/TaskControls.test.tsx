import { render, screen, fireEvent } from '@testing-library/react';
import { TaskControls } from '../components/TaskControls';

describe('TaskControls', () => {
  const mockHandlers = {
    onStart: jest.fn(),
    onPause: jest.fn(),
    onResume: jest.fn(),
    onStop: jest.fn()
  };

  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders start button for pending tasks', () => {
    render(
      <TaskControls
        status="pending"
        {...mockHandlers}
      />
    );
    
    const startButton = screen.getByText('Start');
    expect(startButton).toBeInTheDocument();
    
    fireEvent.click(startButton);
    expect(mockHandlers.onStart).toHaveBeenCalled();
  });

  it('renders pause and stop buttons for running tasks', () => {
    render(
      <TaskControls
        status="running"
        {...mockHandlers}
      />
    );
    
    const pauseButton = screen.getByText('Pause');
    const stopButton = screen.getByText('Stop');
    expect(pauseButton).toBeInTheDocument();
    expect(stopButton).toBeInTheDocument();
    
    fireEvent.click(pauseButton);
    expect(mockHandlers.onPause).toHaveBeenCalled();
    
    fireEvent.click(stopButton);
    expect(mockHandlers.onStop).toHaveBeenCalled();
  });

  it('renders resume and stop buttons for paused tasks', () => {
    render(
      <TaskControls
        status="paused"
        {...mockHandlers}
      />
    );
    
    const resumeButton = screen.getByText('Resume');
    const stopButton = screen.getByText('Stop');
    expect(resumeButton).toBeInTheDocument();
    expect(stopButton).toBeInTheDocument();
    
    fireEvent.click(resumeButton);
    expect(mockHandlers.onResume).toHaveBeenCalled();
    
    fireEvent.click(stopButton);
    expect(mockHandlers.onStop).toHaveBeenCalled();
  });

  it('renders no buttons for completed tasks', () => {
    render(
      <TaskControls
        status="completed"
        {...mockHandlers}
      />
    );
    
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });

  it('renders no buttons for failed tasks', () => {
    render(
      <TaskControls
        status="failed"
        {...mockHandlers}
      />
    );
    
    expect(screen.queryByRole('button')).not.toBeInTheDocument();
  });
}); 