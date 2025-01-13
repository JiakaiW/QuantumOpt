import React from 'react';
import { Box, CircularProgress, Typography } from '@mui/material';

interface LoadingIndicatorProps {
  message?: string;
}

export function LoadingIndicator({ message = 'Loading...' }: LoadingIndicatorProps) {
  return (
    <Box
      sx={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: 'rgba(0, 0, 0, 0.7)',
        zIndex: 9999,
      }}
    >
      <CircularProgress size={60} thickness={4} sx={{ mb: 2 }} />
      <Typography variant="h6" color="white">
        {message}
      </Typography>
    </Box>
  );
} 