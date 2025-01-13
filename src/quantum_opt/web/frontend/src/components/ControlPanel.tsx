import React from 'react';
import { Button, ButtonGroup, Paper, Typography, Box } from '@mui/material';
import { PlayArrow, Pause, Stop } from '@mui/icons-material';

interface ControlPanelProps {
  optimizationId: string | null;
  isRunning: boolean;
  isPaused: boolean;
  onStart: () => void;
  onPause: () => void;
  onResume: () => void;
  onStop: () => void;
}

const ControlPanel: React.FC<ControlPanelProps> = ({
  optimizationId,
  isRunning,
  isPaused,
  onStart,
  onPause,
  onResume,
  onStop
}) => {
  return (
    <Paper sx={{ p: 2, mb: 2 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <Typography variant="h6" component="div" sx={{ mb: 2 }}>
          Optimization Control
          {optimizationId && <Typography variant="caption" display="block">ID: {optimizationId}</Typography>}
        </Typography>
        <ButtonGroup variant="contained">
          {!isRunning ? (
            <Button
              onClick={onStart}
              startIcon={<PlayArrow />}
              color="primary"
            >
              Start
            </Button>
          ) : (
            <>
              <Button
                onClick={isPaused ? onResume : onPause}
                startIcon={isPaused ? <PlayArrow /> : <Pause />}
                color="primary"
              >
                {isPaused ? 'Resume' : 'Pause'}
              </Button>
              <Button
                onClick={onStop}
                startIcon={<Stop />}
                color="error"
              >
                Stop
              </Button>
            </>
          )}
        </ButtonGroup>
      </Box>
    </Paper>
  );
};

export default ControlPanel; 