/// <reference types="vite/client" />

import { useEffect, useRef, useState, useCallback } from 'react';

export interface WebSocketHookResult {
  connected: boolean;
  sendMessage: (message: unknown) => void;
  lastMessage: unknown;
}

export function useWebSocket(path: string): WebSocketHookResult {
  const [connected, setConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<unknown>(null);
  const ws = useRef<WebSocket | null>(null);
  const reconnectAttempts = useRef(0);
  const maxReconnectAttempts = 5;

  const getWebSocketUrl = (path: string) => {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = import.meta.env.DEV ? 'localhost:8000' : window.location.host;
    return `${protocol}//${host}${path}`;
  };

  const connect = useCallback(() => {
    if (ws.current?.readyState === WebSocket.CONNECTING) {
      console.log('WebSocket is already connecting...');
      return;
    }

    try {
      const url = getWebSocketUrl(path);
      console.log('Connecting to WebSocket:', url);
      ws.current = new WebSocket(url);

      ws.current.onopen = () => {
        console.log('WebSocket connected');
        setConnected(true);
        reconnectAttempts.current = 0;
      };

      ws.current.onclose = () => {
        console.log('WebSocket disconnected');
        setConnected(false);
        
        // Attempt to reconnect with exponential backoff
        if (reconnectAttempts.current < maxReconnectAttempts) {
          const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 10000);
          console.log(`Attempting to reconnect in ${delay}ms...`);
          setTimeout(() => {
            reconnectAttempts.current++;
            connect();
          }, delay);
        }
      };

      ws.current.onerror = (error) => {
        console.error('WebSocket error:', error);
      };

      ws.current.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          setLastMessage(data);
        } catch (error) {
          console.error('Error parsing WebSocket message:', error);
          setLastMessage(event.data);
        }
      };
    } catch (error) {
      console.error('Error creating WebSocket connection:', error);
    }
  }, [path]);

  useEffect(() => {
    connect();
    return () => {
      if (ws.current) {
        ws.current.close();
        ws.current = null;
      }
    };
  }, [connect]);

  const sendMessage = useCallback((message: unknown) => {
    if (ws.current?.readyState === WebSocket.OPEN) {
      ws.current.send(JSON.stringify(message));
    } else {
      console.warn('WebSocket is not connected. Message not sent:', message);
    }
  }, []);

  return { connected, sendMessage, lastMessage };
} 