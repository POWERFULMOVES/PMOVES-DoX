"use client";

import { useEffect, useState, useRef } from "react";
import { ArrowLeft, BrainCircuit, Activity, RefreshCw, Send } from "lucide-react";
import Link from "next/link";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import A2UIRenderer from "@/components/a2ui/A2UIRenderer";
import { getNatsWsUrl } from "@/lib/config";

interface A2UIPayload {
  type: string;
  content: any;
  timestamp?: string;
  source?: string;
}

export default function A2UIPage() {
  const [payloads, setPayloads] = useState<A2UIPayload[]>([]);
  const [connected, setConnected] = useState(false);
  const [command, setCommand] = useState("");
  const [commandResult, setCommandResult] = useState<any>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  const connectWebSocket = () => {
    if (wsRef.current?.readyState === WebSocket.OPEN) return;

    const wsUrl = getNatsWsUrl();
    try {
      const ws = new WebSocket(wsUrl);
      wsRef.current = ws;

      ws.onopen = () => {
        console.log("A2UI WebSocket connected");
        setConnected(true);
        // Subscribe to A2UI render subject
        ws.send(JSON.stringify({
          action: "subscribe",
          subject: "a2ui.render.v1"
        }));
      };

      ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (data.subject === "a2ui.render.v1" && data.payload) {
            setPayloads(prev => [
              {
                type: "render",
                content: data.payload,
                timestamp: new Date().toISOString(),
                source: data.source || "agent"
              },
              ...prev
            ].slice(0, 50)); // Keep last 50 payloads
          }
        } catch (e) {
          console.error("Failed to parse WebSocket message:", e);
        }
      };

      ws.onerror = (error) => {
        console.error("WebSocket error:", error);
        setConnected(false);
      };

      ws.onclose = () => {
        console.log("WebSocket closed, reconnecting...");
        setConnected(false);
        // Reconnect after 3 seconds
        reconnectTimeoutRef.current = setTimeout(connectWebSocket, 3000);
      };
    } catch (error) {
      console.error("Failed to connect WebSocket:", error);
      setConnected(false);
    }
  };

  const disconnectWebSocket = () => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
    }
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    setConnected(false);
  };

  const sendCommand = async () => {
    if (!command.trim()) return;

    try {
      const response = await fetch("/api/a2ui/command", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command: command })
      });
      const result = await response.json();
      setCommandResult(result);
    } catch (error) {
      setCommandResult({ error: String(error) });
    }
  };

  useEffect(() => {
    connectWebSocket();
    return () => disconnectWebSocket();
  }, []);

  return (
    <div className="min-h-screen bg-transparent p-8">
      <div className="max-w-7xl mx-auto space-y-8">
        {/* Header */}
        <div className="flex items-center gap-4 mb-8">
          <Link href="/" className="p-2 hover:bg-white/10 rounded-lg transition-colors">
            <ArrowLeft className="w-5 h-5 text-gray-400" />
          </Link>
          <div className="p-3 bg-cyan-100 rounded-xl shadow-sm">
            <BrainCircuit className="w-8 h-8 text-cyan-600" />
          </div>
          <div>
            <h1 className="text-3xl font-extrabold text-white tracking-tight">Agent-to-UI</h1>
            <p className="text-gray-400 mt-1 text-lg">
              Real-time agent-generated UI payloads via NATS
            </p>
          </div>
          <div className="ml-auto flex items-center gap-2">
            <div className={`flex items-center gap-2 px-3 py-1 rounded-full ${
              connected ? "bg-green-500/20 text-green-400" : "bg-red-500/20 text-red-400"
            }`}>
              <Activity className="w-4 h-4" />
              {connected ? "Connected" : "Disconnected"}
            </div>
            {!connected && (
              <Button onClick={connectWebSocket} variant="outline" size="sm">
                <RefreshCw className="w-4 h-4 mr-2" />
                Reconnect
              </Button>
            )}
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Left Column: Payloads */}
          <div className="lg:col-span-2 space-y-6">
            {/* Command Input */}
            <Card className="glass-card border-white/5">
              <CardHeader>
                <CardTitle className="text-lg">Send Command to Agent</CardTitle>
                <CardDescription>
                  Send commands to Agent Zero via MCP API
                </CardDescription>
              </CardHeader>
              <CardContent>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={command}
                    onChange={(e) => setCommand(e.target.value)}
                    onKeyDown={(e) => e.key === "Enter" && sendCommand()}
                    placeholder="Enter command (e.g., 'list available tools')"
                    className="flex-1 px-3 py-2 bg-black/20 border border-white/10 rounded-lg text-white placeholder:text-gray-500 focus:outline-none focus:border-cyan-500"
                  />
                  <Button onClick={sendCommand} disabled={!command.trim()}>
                    <Send className="w-4 h-4 mr-2" />
                    Send
                  </Button>
                </div>
                {commandResult && (
                  <div className="mt-4 p-3 bg-black/30 rounded-lg">
                    <p className="text-xs text-gray-400 mb-1">Command Result:</p>
                    <pre className="text-xs text-green-400 overflow-x-auto">
                      {JSON.stringify(commandResult, null, 2)}
                    </pre>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Incoming Payloads */}
            <Card className="glass-card border-white/5">
              <CardHeader>
                <CardTitle className="text-lg flex items-center justify-between">
                  <span>Incoming A2UI Payloads</span>
                  <span className="text-sm text-gray-400">{payloads.length} received</span>
                </CardTitle>
                <CardDescription>
                  Real-time UI payloads from agents via NATS
                </CardDescription>
              </CardHeader>
              <CardContent>
                {payloads.length === 0 ? (
                  <div className="text-center py-12 text-gray-400">
                    <BrainCircuit className="w-12 h-12 mx-auto mb-4 opacity-50" />
                    <p>Waiting for agent UI payloads...</p>
                    <p className="text-sm mt-2">
                      Subscribe to <code className="text-cyan-400">a2ui.render.v1</code> to receive payloads
                    </p>
                  </div>
                ) : (
                  <div className="space-y-4 max-h-96 overflow-y-auto">
                    {payloads.map((payload, index) => (
                      <div key={index} className="p-3 bg-black/20 rounded-lg border border-white/5">
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-xs text-cyan-400 font-mono">
                            {payload.source || "agent"}
                          </span>
                          <span className="text-xs text-gray-500">
                            {payload.timestamp && new Date(payload.timestamp).toLocaleTimeString()}
                          </span>
                        </div>
                        <A2UIRenderer content={payload.content} />
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Right Column: Info & Stats */}
          <div className="space-y-6">
            <Card className="glass-card border-white/5">
              <CardHeader>
                <CardTitle>NATS Connection</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-400">WebSocket URL</span>
                    <span className="font-mono text-xs">{getNatsWsUrl()}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Subject</span>
                    <span className="font-mono text-xs text-cyan-400">a2ui.render.v1</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-400">Status</span>
                    <span className={connected ? "text-green-400" : "text-red-400"}>
                      {connected ? "Connected" : "Disconnected"}
                    </span>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card className="glass-card border-white/5">
              <CardHeader>
                <CardTitle>What is A2UI?</CardTitle>
              </CardHeader>
              <CardContent className="text-sm text-gray-300 space-y-2">
                <p>
                  Agent-to-UI (A2UI) is a protocol where AI agents generate
                  structured UI payloads that are rendered in real-time.
                </p>
                <p className="text-xs text-gray-400">
                  Agents send JSON payloads describing UI components (buttons, forms, cards)
                  which are dynamically rendered in the frontend.
                </p>
              </CardContent>
            </Card>

            <Card className="glass-card border-white/5">
              <CardHeader>
                <CardTitle>Testing</CardTitle>
              </CardHeader>
              <CardContent className="text-sm">
                <p className="text-gray-300 mb-3">Send a test payload:</p>
                <Button
                  onClick={() => {
                    setPayloads([{
                      type: "test",
                      content: {
                        type: "card",
                        title: "Test Card",
                        description: "This is a test A2UI payload",
                        items: ["Item 1", "Item 2", "Item 3"]
                      },
                      timestamp: new Date().toISOString(),
                      source: "manual"
                    }, ...payloads]);
                  }}
                  variant="outline"
                  className="w-full"
                >
                  Generate Test Payload
                </Button>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}
