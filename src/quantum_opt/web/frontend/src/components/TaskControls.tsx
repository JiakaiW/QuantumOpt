import React from 'react';
import { Button, ButtonGroup } from '@mui/material';
import { PlayArrow, Pause, Stop } from '@mui/icons-material';
import axios from 'axios';

interface TaskControlsProps {
    taskId: string;
    status: string;
    onError: (error: string) => void;
}

export function TaskControls({ taskId, status, onError }: TaskControlsProps) {
    const handleAction = async (action: 'start' | 'pause' | 'stop') => {
        try {
            await axios.post(`http://localhost:8000/api/queue/task/${taskId}/${action}`);
        } catch (err) {
            onError(err instanceof Error ? err.message : 'Failed to control task');
        }
    };

    return (
        <ButtonGroup size="small" aria-label="task controls">
            {status === 'paused' && (
                <Button
                    onClick={() => handleAction('start')}
                    startIcon={<PlayArrow />}
                    sx={{ 
                        fontSize: '0.75rem',
                        textTransform: 'none'
                    }}
                >
                    Resume
                </Button>
            )}
            {status === 'running' && (
                <Button
                    onClick={() => handleAction('pause')}
                    startIcon={<Pause />}
                    sx={{ 
                        fontSize: '0.75rem',
                        textTransform: 'none'
                    }}
                >
                    Pause
                </Button>
            )}
            {(status === 'running' || status === 'paused') && (
                <Button
                    onClick={() => handleAction('stop')}
                    startIcon={<Stop />}
                    color="error"
                    sx={{ 
                        fontSize: '0.75rem',
                        textTransform: 'none'
                    }}
                >
                    Stop
                </Button>
            )}
        </ButtonGroup>
    );
} 