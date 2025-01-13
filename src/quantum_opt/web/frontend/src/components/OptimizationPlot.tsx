import { useEffect, useRef, useMemo, useCallback } from 'react';
import Chart from 'chart.js/auto';
import { debounce } from 'lodash';

interface OptimizationData {
  best_value?: number;
  best_parameters?: Record<string, number>;
  total_evaluations?: number;
  optimization_time?: number;
  optimization_trace?: Array<{
    iteration: number;
    value: number;
    best_value: number;
    timestamp: string;
  }>;
}

interface Props {
  taskId: string;
  data: OptimizationData;
}

// Constants for performance optimization
const MAX_POINTS = 1000; // Maximum number of points to display
const BUFFER_SIZE = 100; // Number of points to keep in memory
const UPDATE_INTERVAL = 100; // Milliseconds between updates

export function OptimizationPlot({ taskId, data }: Props) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const chartRef = useRef<Chart | null>(null);
  const dataBuffer = useRef<{
    iterations: number[];
    values: number[];
    bestValues: number[];
  }>({ iterations: [], values: [], bestValues: [] });

  // Memoize data processing function
  const processData = useCallback((trace: OptimizationData['optimization_trace'] = []) => {
    const newData = {
      iterations: [] as number[],
      values: [] as number[],
      bestValues: [] as number[]
    };

    // If we have more points than MAX_POINTS, downsample the data
    if (trace.length > MAX_POINTS) {
      const step = Math.ceil(trace.length / MAX_POINTS);
      for (let i = 0; i < trace.length; i += step) {
        const point = trace[i];
        newData.iterations.push(point.iteration);
        newData.values.push(point.value);
        newData.bestValues.push(point.best_value);
      }
    } else {
      trace.forEach(point => {
        newData.iterations.push(point.iteration);
        newData.values.push(point.value);
        newData.bestValues.push(point.best_value);
      });
    }

    return newData;
  }, []);

  // Process and buffer new data
  useEffect(() => {
    if (!data.optimization_trace) return;

    const newData = processData(data.optimization_trace);
    dataBuffer.current = newData;
  }, [data.optimization_trace, processData]);

  // Debounced update function with TypedArray support
  const updateChart = useMemo(
    () =>
      debounce((chart: Chart) => {
        if (!chart || !dataBuffer.current) return;

        const { iterations, values, bestValues } = dataBuffer.current;

        // Use TypedArrays for better performance
        const iterationsArray = Float64Array.from(iterations);
        const valuesArray = Float64Array.from(values);
        const bestValuesArray = Float64Array.from(bestValues);

        chart.data.labels = Array.from(iterationsArray);
        chart.data.datasets[0].data = Array.from(valuesArray);
        chart.data.datasets[1].data = Array.from(bestValuesArray);

        // Use requestAnimationFrame for smooth updates
        requestAnimationFrame(() => {
          chart.update('none'); // Use 'none' mode for better performance
        });
      }, UPDATE_INTERVAL),
    []
  );

  useEffect(() => {
    if (!canvasRef.current) return;

    // Create or update chart
    if (!chartRef.current) {
      const ctx = canvasRef.current.getContext('2d');
      if (!ctx) return;

      chartRef.current = new Chart(ctx, {
        type: 'line',
        data: {
          labels: [],
          datasets: [
            {
              label: 'Current Value',
              data: [],
              borderColor: '#000',
              backgroundColor: 'transparent',
              borderWidth: 1,
              pointRadius: 0,
              tension: 0.1,
              spanGaps: true // Improve performance by spanning gaps
            },
            {
              label: 'Best Value',
              data: [],
              borderColor: '#000',
              backgroundColor: 'transparent',
              borderWidth: 2,
              pointRadius: 0,
              tension: 0.1,
              spanGaps: true
            }
          ]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          animation: false, // Disable animations for better performance
          parsing: false, // Disable parsing for better performance
          normalized: true, // Enable normalized stacks for better performance
          elements: {
            line: {
              cubicInterpolationMode: 'monotone' // Smoother lines with better performance
            }
          },
          scales: {
            y: {
              type: 'logarithmic',
              min: 0,
              grid: {
                color: '#f0f0f0',
                display: true
              },
              border: {
                display: false
              },
              ticks: {
                callback: (value: string | number) => 
                  typeof value === 'number' ? value.toExponential(1) : value,
                font: {
                  size: 10,
                  family: '-apple-system, system-ui, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
                },
                color: '#000',
                padding: 8,
                maxTicksLimit: 8 // Limit number of ticks for better performance
              }
            },
            x: {
              grid: {
                display: false
              },
              border: {
                display: false
              },
              ticks: {
                font: {
                  size: 10,
                  family: '-apple-system, system-ui, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
                },
                color: '#000',
                padding: 8,
                maxTicksLimit: 10, // Limit number of ticks for better performance
                source: 'auto' // Let Chart.js decide the best ticks
              }
            }
          },
          plugins: {
            legend: {
              position: 'top',
              align: 'end',
              labels: {
                boxWidth: 12,
                padding: 15,
                font: {
                  size: 11,
                  family: '-apple-system, system-ui, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif'
                },
                color: '#000',
                usePointStyle: true
              }
            },
            decimation: {
              enabled: true,
              algorithm: 'min-max' // Use min-max decimation for better visual representation
            }
          }
        }
      });
    }

    // Update chart data
    updateChart(chartRef.current);

    return () => {
      if (chartRef.current) {
        chartRef.current.destroy();
        chartRef.current = null;
      }
    };
  }, [taskId, updateChart]);

  return (
    <div style={{ 
      padding: '1rem 0',
      height: '300px'
    }}>
      <canvas ref={canvasRef} />
      {data.best_value !== undefined && (
        <div style={{ 
          marginTop: '1.5rem',
          fontSize: '0.75rem',
          color: '#000',
          display: 'flex',
          gap: '1.5rem',
          justifyContent: 'flex-end'
        }}>
          <div>Best Value: {data.best_value.toExponential(4)}</div>
          {data.total_evaluations !== undefined && (
            <div>Evaluations: {data.total_evaluations}</div>
          )}
          {data.optimization_time !== undefined && (
            <div>Time: {data.optimization_time.toFixed(2)}s</div>
          )}
        </div>
      )}
    </div>
  );
} 