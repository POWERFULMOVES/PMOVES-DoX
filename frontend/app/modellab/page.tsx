"use client";

import { useEffect, useState } from "react";
import { ArrowLeft, BrainCircuit, Activity, Zap, Server, TestTube, RefreshCw } from "lucide-react";
import Link from "next/link";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";

interface ModelInfo {
  name: string;
  size?: number;
  digest?: string;
  details?: Record<string, unknown>;
}

interface TensorZeroModel {
  id: string;
  object: string;
  created?: number;
  owned_by?: string;
}

interface ModelsResponse {
  ollama: ModelInfo[];
  tensorzero: TensorZeroModel[];
  services: {
    ollama: string;
    tensorzero: string;
  };
}

interface ModelHealth {
  ollama: { status: string; url: string };
  tensorzero: { status: string; url: string };
}

export default function ModelLabPage() {
  const [models, setModels] = useState<ModelsResponse | null>(null);
  const [health, setHealth] = useState<ModelHealth | null>(null);
  const [loading, setLoading] = useState(true);
  const [testingModel, setTestingModel] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<string | null>(null);

  const fetchModels = async () => {
    setLoading(true);
    try {
      const [modelsData, healthData] = await Promise.all([
        api.getModels(),
        api.getModelHealth(),
      ]);
      setModels(modelsData);
      setHealth(healthData);
    } catch (error) {
      console.error("Failed to fetch models:", error);
    } finally {
      setLoading(false);
    }
  };

  const testModel = async (modelName: string, provider: string) => {
    setTestingModel(modelName);
    setTestResult(null);
    try {
      const result = await api.testModel(modelName, provider, "Hello! Say 'test successful' in one sentence.");
      setTestResult(JSON.stringify(result, null, 2));
    } catch (error) {
      setTestResult(`Error: ${error}`);
    } finally {
      setTestingModel(null);
    }
  };

  useEffect(() => {
    fetchModels();
  }, []);

  const formatSize = (bytes?: number) => {
    if (!bytes) return "Unknown";
    const gb = bytes / (1024 * 1024 * 1024);
    return gb > 1 ? `${gb.toFixed(2)} GB` : `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  const getStatusColor = (status: string) => {
    if (status === "healthy" || status === "ready") return "text-green-400";
    if (status === "unhealthy" || status === "unavailable") return "text-red-400";
    return "text-yellow-400";
  };

  const getStatusIcon = (status: string) => {
    if (status === "healthy" || status === "ready") return <Activity className="h-4 w-4 text-green-400" />;
    if (status === "unhealthy" || status === "unavailable") return <Activity className="h-4 w-4 text-red-400" />;
    return <RefreshCw className="h-4 w-4 text-yellow-400 animate-spin" />;
  };

  return (
    <div className="min-h-screen bg-transparent p-8">
      <div className="max-w-7xl mx-auto space-y-8">
        {/* Header */}
        <div className="flex items-center gap-4 mb-8">
          <Link href="/" className="p-2 hover:bg-white/10 rounded-lg transition-colors">
            <ArrowLeft className="w-5 h-5 text-gray-400" />
          </Link>
          <div className="p-3 bg-purple-100 rounded-xl shadow-sm">
            <BrainCircuit className="w-8 h-8 text-purple-600" />
          </div>
          <div>
            <h1 className="text-3xl font-extrabold text-white tracking-tight">Model Lab</h1>
            <p className="text-gray-400 mt-1 text-lg">
              Real-time model inventory and testing
            </p>
          </div>
          <Button
            onClick={fetchModels}
            variant="outline"
            className="ml-auto"
            disabled={loading}
          >
            <RefreshCw className={`w-4 h-4 mr-2 ${loading ? "animate-spin" : ""}`} />
            Refresh
          </Button>
        </div>

        {/* Service Health */}
        {health && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <Card className="glass-card border-white/5 bg-gradient-to-br from-purple-500/10 to-transparent">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Server className="w-5 h-5" />
                  Ollama Service
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <div className="flex justify-between items-center">
                    <span className="text-muted-foreground">Status</span>
                    <span className={`font-medium ${getStatusColor(health.ollama.status)}`}>
                      {health.ollama.status}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-muted-foreground">URL</span>
                    <span className="font-mono text-xs text-white/60">{health.ollama.url}</span>
                  </div>
                  {models && (
                    <div className="flex justify-between items-center">
                      <span className="text-muted-foreground">Models</span>
                      <span className="font-mono">{models.ollama.length} available</span>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>

            <Card className="glass-card border-white/5 bg-gradient-to-br from-blue-500/10 to-transparent">
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Zap className="w-5 h-5" />
                  TensorZero Gateway
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <div className="flex justify-between items-center">
                    <span className="text-muted-foreground">Status</span>
                    <span className={`font-medium ${getStatusColor(health.tensorzero.status)}`}>
                      {health.tensorzero.status}
                    </span>
                  </div>
                  <div className="flex justify-between items-center">
                    <span className="text-muted-foreground">URL</span>
                    <span className="font-mono text-xs text-white/60">{health.tensorzero.url}</span>
                  </div>
                  {models && (
                    <div className="flex justify-between items-center">
                      <span className="text-muted-foreground">Models</span>
                      <span className="font-mono">{models.tensorzero.length} configured</span>
                    </div>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* Ollama Models */}
        {models && models.ollama.length > 0 && (
          <div className="space-y-4">
            <h2 className="text-xl font-bold text-white flex items-center gap-2">
              <Server className="w-5 h-5 text-purple-400" />
              Ollama Models ({models.ollama.length})
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {models.ollama.map((model) => (
                <Card key={model.name} className="glass-card border-white/5">
                  <CardHeader>
                    <CardTitle className="text-lg truncate">{model.name}</CardTitle>
                    <CardDescription>
                      Size: {formatSize(model.size)}
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3">
                      <div className="text-xs font-mono text-white/50 truncate">
                        {model.digest?.slice(0, 16)}...
                      </div>
                      <Button
                        onClick={() => testModel(model.name, "ollama")}
                        disabled={testingModel === model.name}
                        className="w-full"
                        variant="outline"
                      >
                        <TestTube className="w-4 h-4 mr-2" />
                        {testingModel === model.name ? "Testing..." : "Test Model"}
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        )}

        {/* TensorZero Models */}
        {models && models.tensorzero.length > 0 && (
          <div className="space-y-4">
            <h2 className="text-xl font-bold text-white flex items-center gap-2">
              <Zap className="w-5 h-5 text-blue-400" />
              TensorZero Models ({models.tensorzero.length})
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {models.tensorzero.map((model) => (
                <Card key={model.id} className="glass-card border-white/5">
                  <CardHeader>
                    <CardTitle className="text-lg truncate">{model.id}</CardTitle>
                    <CardDescription>
                      {model.owned_by && `Owner: ${model.owned_by}`}
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <Button
                      onClick={() => testModel(model.id, "tensorzero")}
                      disabled={testingModel === model.id}
                      className="w-full"
                      variant="outline"
                    >
                      <TestTube className="w-4 h-4 mr-2" />
                      {testingModel === model.id ? "Testing..." : "Test Model"}
                    </Button>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        )}

        {/* Test Result */}
        {testResult && (
          <Card className="glass-card border-white/5">
            <CardHeader>
              <CardTitle>Test Result</CardTitle>
            </CardHeader>
            <CardContent>
              <pre className="bg-black/30 p-4 rounded-lg overflow-x-auto text-sm text-green-400">
                {testResult}
              </pre>
            </CardContent>
          </Card>
        )}

        {/* Loading State */}
        {loading && (
          <div className="text-center py-20">
            <RefreshCw className="w-12 h-12 mx-auto mb-4 text-purple-400 animate-spin" />
            <p className="text-gray-400">Loading models...</p>
          </div>
        )}
      </div>
    </div>
  );
}
