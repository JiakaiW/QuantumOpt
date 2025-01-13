import { useState } from 'react';
import axios from 'axios';

export function useOptimization() {
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  const startOptimization = async (taskId: string) => {
    setLoading(true);
    setError(null);
    
    try {
      await axios.post(`http://localhost:8000/api/queue/task/${taskId}/start`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start optimization');
    } finally {
      setLoading(false);
    }
  };

  const cancelOptimization = async (taskId: string) => {
    setLoading(true);
    setError(null);
    
    try {
      await axios.post(`http://localhost:8000/api/queue/task/${taskId}/cancel`);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to cancel optimization');
    } finally {
      setLoading(false);
    }
  };

  return {
    error,
    loading,
    startOptimization,
    cancelOptimization,
  };
} 