import { Paper, Typography, Alert, Snackbar } from '@mui/material';
import { OptimizationPlot } from './components/OptimizationPlot';
import { TaskControls } from './components/TaskControls';
import { useOptimization } from './contexts/OptimizationContext';
import { useState } from 'react';
import './App.css';

function App() {
  const { state, dispatch } = useOptimization();
  const { tasks, connectionStatus, error } = state;
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const handleError = (error: string) => {
    setErrorMessage(error);
  };

  const handleCloseError = () => {
    setErrorMessage(null);
  };

  return (
    <div className="App" style={{ 
      background: '#fff', 
      minHeight: '100vh', 
      padding: '2rem',
      maxWidth: '1200px',
      margin: '0 auto'
    }}>
      <header className="App-header" style={{ 
        marginBottom: '3rem',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        borderBottom: '1px solid #f0f0f0',
        paddingBottom: '1rem'
      }}>
        <Typography variant="h4" component="h1" sx={{ 
          fontWeight: 400,
          fontSize: '1rem',
          color: '#000',
          letterSpacing: '0.05em',
          textTransform: 'uppercase'
        }}>
          QuantumOpt
        </Typography>
        <div className="connection-status" style={{ 
          fontSize: '0.75rem',
          color: '#000',
          letterSpacing: '0.02em'
        }}>
          {connectionStatus === 'connected' ? '● Connected' : '○ Disconnected'}
        </div>
      </header>
      
      <div className="task-list" style={{ display: 'grid', gap: '3rem' }}>
        {Object.values(tasks).length > 0 ? (
          Object.values(tasks).map(task => (
            <Paper 
              key={task.task_id} 
              elevation={0} 
              sx={{ 
                padding: '2rem',
                background: '#fff',
                border: '1px solid #f0f0f0',
                borderRadius: '2px'
              }}
            >
              <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: '2rem'
              }}>
                <div>
                  <Typography variant="h6" sx={{ 
                    fontSize: '0.875rem',
                    fontWeight: 400,
                    color: '#000',
                    letterSpacing: '0.02em',
                    textTransform: 'uppercase',
                    marginBottom: '0.5rem'
                  }}>
                    {task.name}
                  </Typography>
                  <div style={{ 
                    fontSize: '0.75rem',
                    color: '#666',
                    letterSpacing: '0.02em'
                  }}>
                    {task.status}
                  </div>
                </div>
                <TaskControls 
                  taskId={task.task_id} 
                  status={task.status}
                  onError={handleError}
                />
              </div>
              <OptimizationPlot taskId={task.task_id} data={task.result || {}} />
              {task.source_code && (
                <div style={{ 
                  marginTop: '2rem',
                  padding: '1.5rem',
                  background: '#fafafa',
                  borderRadius: '2px',
                  overflow: 'auto'
                }}>
                  <pre style={{ 
                    margin: 0,
                    fontSize: '0.75rem',
                    color: '#000',
                    fontFamily: 'Menlo, Monaco, Consolas, monospace',
                    lineHeight: '1.4'
                  }}>{task.source_code}</pre>
                </div>
              )}
            </Paper>
          ))
        ) : (
          <div style={{ 
            textAlign: 'center',
            padding: '4rem',
            color: '#000',
            fontSize: '0.75rem',
            background: '#fff',
            border: '1px solid #f0f0f0',
            borderRadius: '2px',
            letterSpacing: '0.02em'
          }}>
            No tasks available
          </div>
        )}
      </div>

      <Snackbar 
        open={!!errorMessage} 
        autoHideDuration={6000} 
        onClose={handleCloseError}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert onClose={handleCloseError} severity="error" sx={{ width: '100%' }}>
          {errorMessage}
        </Alert>
      </Snackbar>

      {error && (
        <Alert severity="error" sx={{ marginTop: '2rem' }}>
          {error}
        </Alert>
      )}
    </div>
  );
}

export default App; 