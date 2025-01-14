import { Container, CssBaseline, ThemeProvider, createTheme, Alert } from '@mui/material';
import { TaskForm } from './components/TaskForm';
import { TaskList } from './components/TaskList';
import { OptimizationProvider, useOptimizationContext } from './contexts/OptimizationContext';

const theme = createTheme({
  palette: {
    mode: 'dark',
    primary: {
      main: '#90caf9'  // A lighter blue that works well in dark mode
    },
    secondary: {
      main: '#f48fb1'  // A lighter pink that works well in dark mode
    },
    background: {
      default: '#121212',
      paper: '#1e1e1e'
    }
  }
});

function ConnectionStatus() {
  const { state } = useOptimizationContext();
  return (
    <Alert 
      severity={state.connected ? "success" : "error"}
      sx={{ mb: 2 }}
    >
      {state.connected ? "Connected to server" : "Disconnected from server"}
    </Alert>
  );
}

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <OptimizationProvider>
        <Container maxWidth="lg" sx={{ py: 4 }}>
          <ConnectionStatus />
          <TaskForm />
          <TaskList />
        </Container>
      </OptimizationProvider>
    </ThemeProvider>
  );
}

export default App; 