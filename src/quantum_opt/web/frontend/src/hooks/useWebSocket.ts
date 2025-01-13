import { useState, useEffect, useCallback } from 'react';

export function useWebSocket(url: string) {
  const [socket, setSocket] = useState<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);
  const [lastMessage, setLastMessage] = useState<string | null>(null);

  useEffect(() => {
    const ws = new WebSocket(url);

    ws.onopen = () => {
      console.log('WebSocket connected');
      setConnected(true);
    };

    ws.onclose = () => {
      console.log('WebSocket disconnected');
      setConnected(false);
    };

    ws.onmessage = (event) => {
      setLastMessage(event.data);
    };

    setSocket(ws);

    return () => {
      ws.close();
    };
  }, [url]);

  const sendMessage = useCallback((message: string) => {
    if (socket?.readyState === WebSocket.OPEN) {
      socket.send(message);
    }
  }, [socket]);

  return { connected, lastMessage, sendMessage };
} 