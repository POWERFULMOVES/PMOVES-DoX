'use client';

import React, { createContext, useContext, useEffect, useState } from 'react';
import { connect, NatsConnection, StringCodec, Subscription } from 'nats.ws';

interface NatsContextType {
  connection: NatsConnection | null;
  isConnected: boolean;
  error: Error | null;
  publish: (subject: string, data: any) => void;
  lastMessage: any; // Simplified for basic usage
}

const NatsContext = createContext<NatsContextType>({
  connection: null,
  isConnected: false,
  error: null,
  publish: () => {},
  lastMessage: null,
});

export const useNats = () => useContext(NatsContext);

interface NatsProviderProps {
  children: React.ReactNode;
  servers?: string[];
}

export function NatsProvider({ children, servers = ['ws://localhost:9223'] }: NatsProviderProps) {
  const [connection, setConnection] = useState<NatsConnection | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [lastMessage, setLastMessage] = useState<any>(null);

  useEffect(() => {
    let nc: NatsConnection;

    const initNats = async () => {
      try {
        console.log(`Attempting to connect to NATS at ${servers[0]}...`);
        nc = await connect({ servers: servers });
        console.log('Connected to NATS via WebSockets!');
        setConnection(nc);
        setIsConnected(true);
        setError(null);

        // Optional: Monitor closed connection
        (async () => {
          for await (const s of nc.status()) {
             console.log(`NATS Status: ${s.type}: ${s.data}`);
          }
        })().then();

      } catch (err: any) {
        console.error('Failed to connect to NATS:', err);
        setError(err);
        setIsConnected(false);
      }
    };

    initNats();

    return () => {
      if (nc) {
        nc.close().then(() => console.log('NATS Connection closed.'));
      }
    };
  }, [servers]);

  const publish = (subject: string, data: any) => {
    if (connection) {
      const sc = StringCodec();
      connection.publish(subject, sc.encode(JSON.stringify(data)));
    } else {
        console.warn("Cannot publish, NATS not connected.");
    }
  };

  return (
    <NatsContext.Provider value={{ connection, isConnected, error, publish, lastMessage }}>
      {children}
    </NatsContext.Provider>
  );
}
