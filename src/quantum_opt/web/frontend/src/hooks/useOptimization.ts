import { useState, useCallback } from 'react';
import axios from 'axios';

type OptimizationStatus = 'idle' | 'running' | 'paused' | 'completed' | 'error';

export function useOptimization() {
  const [status, setStatus] = useState<OptimizationStatus>('idle');
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const startOptimization = useCallback(async (config: any) => {
    try {
      const response = await axios.post('/api/optimization', config);
      setStatus('running');
      return response.data;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start optimization');
      setStatus('error');
    }
  }, []);

  const pauseOptimization = useCallback(async () => {
    try {
      await axios.post('/api/optimization/pause');
      setStatus('paused');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to pause optimization');
    }
  }, []);

  const resumeOptimization = useCallback(async () => {
    try {
      await axios.post('/api/optimization/resume');
      setStatus('running');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to resume optimization');
    }
  }, []);

  const stopOptimization = useCallback(async () => {
    try {
      await axios.post('/api/optimization/stop');
      setStatus('idle');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to stop optimization');
    }
  }, []);

  return {
    status,
    progress,
    error,
    startOptimization,
    pauseOptimization,
    resumeOptimization,
    stopOptimization,
  };
} 