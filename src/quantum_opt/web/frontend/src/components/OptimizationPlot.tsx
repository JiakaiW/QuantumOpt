import { Box, Typography } from '@mui/material';
import { Line } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  ChartOptions,
  ChartData
} from 'chart.js';

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
);

interface OptimizationTrace {
  iteration: number;
  value: number;
  best_value: number;
  timestamp: string;
}

interface Task {
  task_id: string;
  status: string;
  result?: {
    optimization_trace: OptimizationTrace[];
    best_value?: number;
  };
}

interface OptimizationPlotProps {
  task: Task;
}

export function OptimizationPlot({ task }: OptimizationPlotProps) {
  if (!task.result?.optimization_trace || task.result.optimization_trace.length === 0) {
    return (
      <Box sx={{ height: 400, width: '100%', p: 2, bgcolor: 'background.paper' }}>
        <Typography variant="body2" color="text.secondary" align="center">
          No optimization data available
        </Typography>
        <Line data={{ datasets: [] }} options={{ responsive: true, maintainAspectRatio: false }} />
      </Box>
    );
  }

  const trace = task.result.optimization_trace;
  
  // Debug logs to track data flow
  console.log('OptimizationPlot received trace:', {
    length: trace.length,
    first: trace[0],
    last: trace[trace.length - 1],
    task_status: task.status,
    all_points: trace.map(t => ({
      iteration: t.iteration,
      value: t.value,
      best_value: t.best_value
    }))
  });
  
  // Filter out any points with undefined values
  const validTrace = trace.filter(point => {
    const isValid = typeof point.iteration === 'number' && 
                   typeof point.value === 'number' &&
                   typeof point.best_value === 'number';
    if (!isValid) {
      console.warn('Invalid trace point:', point);
    }
    return isValid;
  });

  console.log('Valid trace points:', {
    total: trace.length,
    valid: validTrace.length,
    points: validTrace
  });

  // Only proceed if we have valid data points
  if (validTrace.length === 0) {
    return (
      <Typography variant="body2" color="text.secondary" align="center">
        Waiting for valid optimization data...
      </Typography>
    );
  }

  // Use the actual evaluated values for each iteration
  const evaluatedValues = validTrace.map((point) => ({
    x: point.iteration,
    y: point.value  // Always use the evaluated value
  }));

  // For best values, create a monotonically decreasing sequence
  let currentBest = Infinity;
  const bestValues = validTrace.map((point) => {
    currentBest = Math.min(currentBest, point.best_value);
    return {
      x: point.iteration,
      y: currentBest
    };
  });

  console.log('Plot data:', {
    evaluatedValues,
    bestValues
  });

  const maxIteration = Math.max(...validTrace.map(p => p.iteration));
  const maxValue = Math.max(...evaluatedValues.map(p => p.y));
  const minValue = Math.min(...evaluatedValues.map(p => p.y));
  const valueMargin = (maxValue - minValue) * 0.1;

  const chartData: ChartData<'line'> = {
    datasets: [
      {
        label: 'Evaluated Values',
        data: evaluatedValues,
        borderColor: 'rgba(75, 192, 192, 0.8)',
        backgroundColor: 'rgba(75, 192, 192, 0.8)',
        pointRadius: 4,
        pointHoverRadius: 6,
        showLine: false,
        order: 2
      },
      {
        label: 'Best Value',
        data: bestValues,
        borderColor: 'rgba(255, 99, 132, 1)',
        backgroundColor: 'rgba(255, 99, 132, 0.2)',
        pointRadius: 0,
        borderWidth: 2,
        tension: 0,
        fill: false,
        order: 1
      }
    ]
  };

  const chartOptions: ChartOptions<'line'> = {
    responsive: true,
    maintainAspectRatio: false,
    animation: {
      duration: 0 // Disable animations for better performance
    },
    scales: {
      x: {
        type: 'linear',
        display: true,
        title: {
          display: true,
          text: 'Iteration'
        },
        min: 0,
        max: maxIteration + 1,
        ticks: {
          stepSize: Math.max(1, Math.floor(maxIteration / 10))
        }
      },
      y: {
        type: 'linear',
        display: true,
        title: {
          display: true,
          text: 'Objective Value'
        },
        min: minValue - valueMargin,
        max: maxValue + valueMargin
      }
    },
    plugins: {
      legend: {
        display: true,
        position: 'top',
        labels: {
          usePointStyle: true,
          pointStyle: 'circle'
        }
      },
      tooltip: {
        enabled: true,
        mode: 'nearest',
        intersect: true
      }
    }
  };

  return (
    <Box sx={{ height: 400, width: '100%', p: 2, bgcolor: 'background.paper' }}>
      <Line data={chartData} options={chartOptions} />
    </Box>
  );
} 