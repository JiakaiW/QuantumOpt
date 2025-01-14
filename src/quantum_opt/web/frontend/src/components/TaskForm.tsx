import React, { useState } from 'react';
import { 
  Paper, TextField, Button, Box, Typography, Alert, Snackbar,
  IconButton, Select, MenuItem, FormControl, InputLabel, Grid
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import DeleteIcon from '@mui/icons-material/Delete';
import { useOptimizationContext } from '../contexts/OptimizationContext';

interface ParameterConfig {
  lower_bound: number;
  upper_bound: number;
  init?: number;
  scale: 'linear' | 'log';
}

interface OptimizationConfig {
  name: string;
  parameter_config: Record<string, ParameterConfig>;
  objective_fn: string;
  optimizer_config: {
    optimizer_type: 'OnePlusOne' | 'CMA';
    budget: number;
    num_workers: number;
  };
  execution_config?: {
    max_retries: number;
    timeout: number;
  };
}

const defaultObjectiveFunction = `def objective(x: float) -> float:
    """Example objective function that minimizes distance from x=1.
    
    Args:
        x: Value to optimize between bounds
    Returns:
        float: Value to be minimized
    """
    return (x - 1.0)**2  # Minimize distance from x=1
`;

interface Parameter extends ParameterConfig {
  name: string;
  description?: string;
}

export function TaskForm() {
  const { dispatch } = useOptimizationContext();
  const [parameters, setParameters] = useState<Parameter[]>([{
    name: 'x',
    lower_bound: -5.0,
    upper_bound: 5.0,
    init: 0.0,
    scale: 'linear',
    description: 'First parameter'
  }]);

  const [name, setName] = useState('New Optimization Task');
  const [objectiveFn, setObjectiveFn] = useState(defaultObjectiveFunction);
  const [optimizerType, setOptimizerType] = useState<'OnePlusOne' | 'CMA'>('OnePlusOne');
  const [budget, setBudget] = useState(100);
  const [numWorkers, setNumWorkers] = useState(1);
  
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  const [optimizerConfig, setOptimizerConfig] = useState({
    optimizer_type: 'CMA',
    budget: 100,
    num_workers: 4
  });

  const handleAddParameter = () => {
    setParameters(prev => [...prev, {
      name: `param${prev.length + 1}`,
      lower_bound: -5.0,
      upper_bound: 5.0,
      init: 0.0,
      scale: 'linear',
      description: `Parameter ${prev.length + 1}`
    }]);
  };

  const handleRemoveParameter = (index: number) => {
    setParameters(prev => prev.filter((_, i) => i !== index));
  };

  const handleParameterChange = (index: number, field: keyof Parameter, value: any) => {
    setParameters(prev => prev.map((param, i) => 
      i === index ? { ...param, [field]: value } : param
    ));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    
    try {
      // Convert parameters array to required format
      const parameter_config = parameters.reduce<Record<string, ParameterConfig>>((acc, param) => ({
        ...acc,
        [param.name]: {
          lower_bound: param.lower_bound,
          upper_bound: param.upper_bound,
          init: param.init,
          scale: param.scale
        }
      }), {});

      const requestBody: OptimizationConfig = {
        name,
        parameter_config,
        objective_fn: objectiveFn,
        optimizer_config: {
          optimizer_type: optimizerType,
          budget,
          num_workers: numWorkers
        },
        execution_config: {
          max_retries: 3,
          timeout: 3600.0
        }
      };

      console.log('Sending request with body:', JSON.stringify(requestBody, null, 2));

      const response = await fetch('/api/v1/tasks', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(requestBody),
      });

      console.log('Response status:', response.status);
      const responseText = await response.text();
      console.log('Response text:', responseText);

      if (!response.ok) {
        let errorMessage;
        try {
          const errorData = JSON.parse(responseText);
          errorMessage = errorData.error?.message || errorData.error?.detail || errorData.detail || 'Failed to create task';
          console.error('Parsed error data:', errorData);
        } catch (parseError) {
          console.error('Error parsing response:', parseError);
          errorMessage = responseText || 'Failed to create task';
        }
        throw new Error(errorMessage);
      }
      
      let data;
      try {
        data = JSON.parse(responseText);
      } catch (parseError) {
        console.error('Error parsing success response:', parseError);
        throw new Error('Invalid response from server');
      }

      if (data.status === 'success') {
        // Dispatch the ADD_TASK action
        dispatch({
          type: 'ADD_TASK',
          payload: {
            task_id: data.data.task_id,
            task: {
              task_id: data.data.task_id,
              status: 'pending',
              result: {
                optimization_trace: [],
                best_value: undefined
              }
            }
          }
        });

        setSuccess(true);
        // Reset form to default values
        setParameters([{
          name: 'x',
          lower_bound: -5.0,
          upper_bound: 5.0,
          init: 0.0,
          scale: 'linear',
          description: 'First parameter'
        }]);
        setName('New Optimization Task');
        setObjectiveFn(defaultObjectiveFunction);
        setOptimizerType('OnePlusOne');
        setBudget(100);
        setNumWorkers(1);
      } else {
        console.error('Unsuccessful response:', data);
        throw new Error(data.error?.message || data.error?.detail || 'Failed to create task');
      }
    } catch (error) {
      console.error('Error creating task:', error);
      setError(error instanceof Error ? error.message : 'Failed to create task');
    }
  };

  return (
    <Paper sx={{ p: 2, mt: 2 }}>
      <Typography variant="h6" gutterBottom>
        Create New Optimization Task
      </Typography>
      <form onSubmit={handleSubmit}>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          <TextField
            label="Task Name"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />
          
          <Box sx={{ mb: 2 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', mb: 1 }}>
              <Typography variant="subtitle1">Parameters</Typography>
              <IconButton onClick={handleAddParameter} size="small" sx={{ ml: 1 }}>
                <AddIcon />
              </IconButton>
            </Box>
            
            {parameters.map((param, index) => (
              <Box key={index} sx={{ 
                display: 'flex', 
                gap: 2, 
                flexWrap: 'wrap', 
                p: 2, 
                mb: 2,
                border: '1px solid #ddd', 
                borderRadius: 1,
                position: 'relative'
              }}>
                <IconButton 
                  onClick={() => handleRemoveParameter(index)}
                  size="small"
                  sx={{ position: 'absolute', right: 8, top: 8 }}
                >
                  <DeleteIcon />
                </IconButton>
                
                <TextField
                  label="Parameter Name"
                  value={param.name}
                  onChange={(e) => handleParameterChange(index, 'name', e.target.value)}
                  required
                  sx={{ width: '200px' }}
                />
                
                <TextField
                  label="Description"
                  value={param.description}
                  onChange={(e) => handleParameterChange(index, 'description', e.target.value)}
                  sx={{ width: '300px' }}
                />
                
                <FormControl sx={{ width: '120px' }}>
                  <InputLabel>Scale</InputLabel>
                  <Select
                    value={param.scale}
                    label="Scale"
                    onChange={(e) => handleParameterChange(index, 'scale', e.target.value as 'linear' | 'log')}
                  >
                    <MenuItem value="linear">Linear</MenuItem>
                    <MenuItem value="log">Log</MenuItem>
                  </Select>
                </FormControl>
                
                <TextField
                  label="Lower Bound"
                  type="number"
                  value={param.lower_bound}
                  onChange={(e) => {
                    const value = e.target.value;
                    handleParameterChange(index, 'lower_bound', value === '' ? 0 : parseFloat(value));
                  }}
                  required
                  sx={{ width: '150px' }}
                />
                
                <TextField
                  label="Upper Bound"
                  type="number"
                  value={param.upper_bound}
                  onChange={(e) => {
                    const value = e.target.value;
                    handleParameterChange(index, 'upper_bound', value === '' ? 0 : parseFloat(value));
                  }}
                  required
                  sx={{ width: '150px' }}
                />
                
                <TextField
                  label="Initial Value"
                  type="number"
                  value={param.init === undefined ? '' : param.init}
                  onChange={(e) => {
                    const value = e.target.value;
                    handleParameterChange(index, 'init', value === '' ? undefined : parseFloat(value));
                  }}
                  sx={{ width: '150px' }}
                />
              </Box>
            ))}
          </Box>
          
          <TextField
            label="Objective Function"
            multiline
            rows={8}
            value={objectiveFn}
            onChange={(e) => setObjectiveFn(e.target.value)}
            required
            sx={{ 
              fontFamily: 'monospace',
              '& .MuiInputBase-input': {
                fontFamily: 'monospace'
              }
            }}
          />
          
          <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
            <FormControl sx={{ minWidth: 200 }}>
              <InputLabel>Optimizer Type</InputLabel>
              <Select
                value={optimizerType}
                label="Optimizer Type"
                onChange={(e) => setOptimizerType(e.target.value as 'OnePlusOne' | 'CMA')}
              >
                <MenuItem value="OnePlusOne">OnePlusOne</MenuItem>
                <MenuItem value="CMA">CMA</MenuItem>
              </Select>
            </FormControl>
            
            <TextField
              label="Budget"
              type="number"
              value={budget}
              onChange={(e) => setBudget(parseInt(e.target.value))}
              inputProps={{ min: 1 }}
              required
              sx={{ width: 150 }}
            />
            
            <TextField
              label="Number of Workers"
              type="number"
              value={numWorkers}
              onChange={(e) => setNumWorkers(parseInt(e.target.value))}
              inputProps={{ min: 1 }}
              required
              sx={{ width: 150 }}
            />
          </Box>
          
          <Box sx={{ mt: 3 }}>
            <Typography variant="h6" gutterBottom>Optimizer Configuration</Typography>
            <Grid container spacing={2}>
              <Grid item xs={12} sm={6}>
                <FormControl fullWidth>
                  <InputLabel>Optimizer Type</InputLabel>
                  <Select
                    value={optimizerConfig.optimizer_type}
                    onChange={(e) => setOptimizerConfig({
                      ...optimizerConfig,
                      optimizer_type: e.target.value as 'CMA' | 'OnePlusOne'
                    })}
                  >
                    <MenuItem value="CMA">CMA</MenuItem>
                    <MenuItem value="OnePlusOne">OnePlusOne</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              <Grid item xs={12} sm={6}>
                <TextField
                  fullWidth
                  label="Budget"
                  type="number"
                  value={optimizerConfig.budget}
                  onChange={(e) => setOptimizerConfig({
                    ...optimizerConfig,
                    budget: parseInt(e.target.value)
                  })}
                />
              </Grid>
              <Grid item xs={12}>
                <TextField
                  fullWidth
                  label="Number of Workers"
                  type="number"
                  value={optimizerConfig.num_workers}
                  onChange={(e) => setOptimizerConfig({
                    ...optimizerConfig,
                    num_workers: parseInt(e.target.value)
                  })}
                />
              </Grid>
            </Grid>
          </Box>
          
          <Button 
            type="submit" 
            variant="contained" 
            color="primary"
            sx={{ mt: 2 }}
          >
            Create Task
          </Button>
        </Box>
        
        {error && (
          <Alert severity="error" sx={{ mt: 2 }}>
            {error}
          </Alert>
        )}
      </form>
      
      <Snackbar
        open={success}
        autoHideDuration={3000}
        onClose={() => setSuccess(false)}
        message="Task created successfully"
      />
    </Paper>
  );
} 