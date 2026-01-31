'use client';

import React, { createContext, useContext, useEffect, useState, useCallback, useRef } from 'react';
import { connect, NatsConnection, StringCodec, Subscription } from 'nats.ws';

interface NatsContextType {
  connection: NatsConnection | null;
  isConnected: boolean;
  error: Error | null;
  reconnectAttempt: number;
  publish: (subject: string, data: any) => void;
  lastMessage: any; // Simplified for basic usage
}

const NatsContext = createContext<NatsContextType>({
  connection: null,
  isConnected: false,
  error: null,
  reconnectAttempt: 0,
  publish: () => {},
  lastMessage: null,
});

export const useNats = () => useContext(NatsContext);

interface NatsProviderProps {
  children: React.ReactNode;
  servers?: string[];
  maxReconnectAttempts?: number;
  reconnectBaseDelay?: number;
  maxReconnectDelay?: number;
}

export function NatsProvider({
  children,
  servers = [process.env.NEXT_PUBLIC_NATS_WS_URL || 'ws://localhost:9223'],
  maxReconnectAttempts = 5,
  reconnectBaseDelay = 1000,
  maxReconnectDelay = 30000,
}: NatsProviderProps) {
  const [connection, setConnection] = useState<NatsConnection | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [lastMessage, setLastMessage] = useState<any>(null);
  const [reconnectAttempt, setReconnectAttempt] = useState(0);

  // Use refs to track connection state across reconnection attempts
  const ncRef = useRef<NatsConnection | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const isMountedRef = useRef(true);

  // Exponential backoff with jitter
  const getReconnectDelay = useCallback((attempt: number) => {
    const baseDelay = reconnectBaseDelay * Math.pow(2, attempt);
    const jitter = Math.random() * 0.3 * baseDelay; // 0-30% jitter
    return Math.min(baseDelay + jitter, maxReconnectDelay);
  }, [reconnectBaseDelay, maxReconnectDelay]);

  // Reconnection logic
  const attemptReconnect = useCallback(async (attempt: number = 1): Promise<void> => {
    if (!isMountedRef.current) return;
    if (attempt > maxReconnectAttempts) {
      console.warn(`NATS: Max reconnect attempts (${maxReconnectAttempts}) reached. Giving up.`);
      return;
    }

    const delay = getReconnectDelay(attempt - 1);
    console.log(`NATS: Reconnect attempt ${attempt}/${maxReconnectAttempts} in ${Math.round(delay)}ms...`);
    setReconnectAttempt(attempt);

    reconnectTimeoutRef.current = setTimeout(async () => {
      if (!isMountedRef.current) return;

      try {
        const nc = await connect({ servers });
        console.log('NATS: Reconnected successfully!');
        ncRef.current = nc;
        setConnection(nc);
        setIsConnected(true);
        setError(null);
        setReconnectAttempt(0);

        // Monitor for disconnection to trigger reconnect
        monitorConnection(nc);
      } catch (err: any) {
        console.error(`NATS: Reconnect attempt ${attempt} failed:`, err);
        setError(err);
        // Schedule next attempt
        attemptReconnect(attempt + 1);
      }
    }, delay);
  }, [servers, maxReconnectAttempts, getReconnectDelay]);

  // Monitor connection status and trigger reconnect on disconnect
  const monitorConnection = useCallback((nc: NatsConnection) => {
    (async () => {
      for await (const status of nc.status()) {
        console.log(`NATS Status: ${status.type}`, status.data || '');

        if (status.type === 'disconnect' || status.type === 'error') {
          if (isMountedRef.current) {
            setIsConnected(false);
            // Only attempt reconnect if we haven't started one already
            if (reconnectAttempt === 0) {
              attemptReconnect(1);
            }
          }
        } else if (status.type === 'reconnect') {
          if (isMountedRef.current) {
            setIsConnected(true);
            setReconnectAttempt(0);
          }
        }
      }
    })().catch(err => {
      console.error('NATS status monitor error:', err);
    });
  }, [attemptReconnect, reconnectAttempt]);

  useEffect(() => {
    isMountedRef.current = true;

    const initNats = async () => {
      try {
        console.log(`NATS: Connecting to ${servers[0]}...`);
        const nc = await connect({ servers });
        console.log('NATS: Connected via WebSockets!');
        ncRef.current = nc;
        setConnection(nc);
        setIsConnected(true);
        setError(null);

        // Monitor connection status
        monitorConnection(nc);
      } catch (err: any) {
        console.error('NATS: Initial connection failed:', err);
        setError(err);
        setIsConnected(false);
        // Start reconnection attempts
        attemptReconnect(1);
      }
    };

    initNats();

    return () => {
      isMountedRef.current = false;
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
      if (ncRef.current) {
        ncRef.current.close().then(() => console.log('NATS: Connection closed.'));
      }
    };
  }, [servers, monitorConnection, attemptReconnect]);

  const publish = (subject: string, data: any) => {
    if (connection) {
      const sc = StringCodec();
      connection.publish(subject, sc.encode(JSON.stringify(data)));
    } else {
        console.warn("Cannot publish, NATS not connected.");
    }
  };

  return (
    <NatsContext.Provider value={{ connection, isConnected, error, reconnectAttempt, publish, lastMessage }}>
      {children}
    </NatsContext.Provider>
  );
}
