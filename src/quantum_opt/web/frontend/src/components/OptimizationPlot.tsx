import React, { useEffect, useRef } from 'react';
import { Line } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
} from 'chart.js';

// Register ChartJS components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
);

interface OptimizationPlotProps {
  taskId: string;
  data: {
    iterations: number[];
    values: number[];
    bestValues: number[];
  };
}

const OptimizationPlot: React.FC<OptimizationPlotProps> = ({ taskId, data }) => {
  const chartData = {
    labels: data.iterations,
    datasets: [
      {
        label: 'Current Value',
        data: data.values,
        borderColor: 'rgb(75, 192, 192)',
        backgroundColor: 'rgba(75, 192, 192, 0.5)',
        tension: 0.1
      },
      {
        label: 'Best Value',
        data: data.bestValues,
        borderColor: 'rgb(255, 99, 132)',
        backgroundColor: 'rgba(255, 99, 132, 0.5)',
        tension: 0
      }
    ]
  };

  const options = {
    responsive: true,
    animation: {
      duration: 0 // Disable animation for better performance
    },
    plugins: {
      title: {
        display: true,
        text: `Optimization Progress - Task ${taskId}`
      },
      legend: {
        position: 'top' as const
      }
    },
    scales: {
      y: {
        type: 'linear' as const,
        display: true,
        position: 'left' as const,
        title: {
          display: true,
          text: 'Objective Value'
        }
      },
      x: {
        title: {
          display: true,
          text: 'Iteration'
        }
      }
    }
  };

  return (
    <div style={{ width: '100%', height: '400px', padding: '20px' }}>
      <Line data={chartData} options={options} />
    </div>
  );
};

export default OptimizationPlot; 