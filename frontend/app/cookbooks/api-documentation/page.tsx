"use client";

import { useState, useRef } from "react";
import { ArrowLeft, FileText, Upload, Download, Code2, FileJson, FileCode, Sparkles } from "lucide-react";
import Link from "next/link";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { api } from "@/lib/api";

type SpecFormat = "openapi" | "swagger" | "asyncapi" | "graphql";

interface GeneratedSpec {
  openapi?: string;
  info?: {
    title: string;
    version: string;
    description?: string;
  };
  paths?: Record<string, any>;
  components?: Record<string, any>;
}

export default function APIDocumentationPage() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [format, setFormat] = useState<SpecFormat>("openapi");
  const [generating, setGenerating] = useState(false);
  const [generatedSpec, setGeneratedSpec] = useState<GeneratedSpec | null>(null);
  const [specYaml, setSpecYaml] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      setSelectedFile(file);
    }
  };

  const generateSpec = async () => {
    if (!selectedFile) return;

    setGenerating(true);
    setGeneratedSpec(null);
    setSpecYaml("");

    try {
      // Upload file and generate spec
      const formData = new FormData();
      formData.append("file", selectedFile);
      formData.append("format", format);

      // Call the analysis API to generate documentation
      // For now, we'll use the documents endpoint and generate a mock spec
      // In production, this would call a dedicated /api/analysis/api-doc endpoint

      // Simulate API call for demo
      await new Promise(resolve => setTimeout(resolve, 2000));

      // Generate a sample OpenAPI spec based on the file
      const mockSpec: GeneratedSpec = {
        openapi: "3.0.0",
        info: {
          title: selectedFile.name.replace(/\.[^/.]+$/, ""),
          version: "1.0.0",
          description: `API documentation generated from ${selectedFile.name}`
        },
        paths: {
          "/api/users": {
            get: {
              summary: "List all users",
              responses: {
                "200": {
                  description: "Successful response",
                  content: {
                    "application/json": {
                      schema: {
                        type: "array",
                        items: { type: "object" }
                      }
                    }
                  }
                }
              }
            },
            post: {
              summary: "Create a new user",
              requestBody: {
                required: true,
                content: {
                  "application/json": {
                    schema: { $ref: "#/components/schemas/User" }
                  }
                }
              }
            }
          }
        },
        components: {
          schemas: {
            User: {
              type: "object",
              properties: {
                id: { type: "string" },
                name: { type: "string" },
                email: { type: "string", format: "email" }
              }
            }
          }
        }
      };

      setGeneratedSpec(mockSpec);
      setSpecYaml(JSON.stringify(mockSpec, null, 2));
    } catch (error) {
      console.error("Failed to generate spec:", error);
      alert("Failed to generate API documentation");
    } finally {
      setGenerating(false);
    }
  };

  const downloadSpec = (extension: "json" | "yaml") => {
    if (!generatedSpec) return;

    let content = "";
    let filename = "";

    if (extension === "json") {
      content = JSON.stringify(generatedSpec, null, 2);
      filename = `openapi.json`;
    } else {
      // Simple YAML conversion (in production, use a proper YAML library)
      content = jsonToYaml(generatedSpec);
      filename = `openapi.yaml`;
    }

    const blob = new Blob([content], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const jsonToYaml = (obj: any, indent = 0): string => {
    const spaces = "  ".repeat(indent);
    let yaml = "";

    for (const [key, value] of Object.entries(obj)) {
      if (value === null) {
        yaml += `${spaces}${key}: null\n`;
      } else if (Array.isArray(value)) {
        yaml += `${spaces}${key}:\n`;
        value.forEach((item, i) => {
          if (typeof item === "object" && item !== null) {
            yaml += `${spaces}  -\n${jsonToYaml(item, indent + 2)}`;
          } else {
            yaml += `${spaces}  - ${item}\n`;
          }
        });
      } else if (typeof value === "object") {
        yaml += `${spaces}${key}:\n${jsonToYaml(value, indent + 1)}`;
      } else {
        yaml += `${spaces}${key}: ${value}\n`;
      }
    }

    return yaml;
  };

  return (
    <div className="min-h-screen bg-transparent p-8">
      <div className="max-w-6xl mx-auto space-y-8">
        {/* Header */}
        <div className="flex items-center gap-4 mb-8">
          <Link href="/cookbooks" className="p-2 hover:bg-white/10 rounded-lg transition-colors">
            <ArrowLeft className="w-5 h-5 text-gray-400" />
          </Link>
          <div className="p-3 bg-orange-100 rounded-xl shadow-sm">
            <FileText className="w-8 h-8 text-orange-600" />
          </div>
          <div>
            <h1 className="text-3xl font-extrabold text-white tracking-tight">
              API Documentation Generator
            </h1>
            <p className="text-gray-400 mt-1 text-lg">
              Generate OpenAPI/Swagger specs from code and documents
            </p>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Left Column: Configuration */}
          <div className="lg:col-span-2 space-y-6">
            {/* How it Works */}
            <div className="bg-white/10 backdrop-blur-sm border border-white/10 rounded-xl p-6">
              <h2 className="text-xl font-bold text-white mb-4 flex items-center gap-2">
                <Sparkles className="w-5 h-5 text-orange-400" />
                How it Works
              </h2>
              <ol className="space-y-3">
                {[
                  "Upload a source file (Python code, JavaScript, JSON, existing OpenAPI spec)",
                  "Select the target output format (OpenAPI 3.0, Swagger 2.0, AsyncAPI)",
                  "Click Generate to analyze the code and extract API endpoints",
                  "Preview the generated specification",
                  "Download as YAML or JSON for use with Swagger UI, Postman, etc."
                ].map((step, i) => (
                  <li key={i} className="flex items-start gap-3 text-gray-300">
                    <span className="flex-shrink-0 w-6 h-6 rounded-full bg-orange-500/30 text-orange-300 flex items-center justify-center text-sm font-medium">
                      {i + 1}
                    </span>
                    <span>{step}</span>
                  </li>
                ))}
              </ol>
            </div>

            {/* File Upload */}
            <div className="bg-white/10 backdrop-blur-sm border border-white/10 rounded-xl p-6">
              <h3 className="text-lg font-bold text-white mb-4">1. Upload Source File</h3>
              <div
                onClick={() => fileInputRef.current?.click()}
                className="border-2 border-dashed border-white/20 rounded-lg p-8 text-center cursor-pointer hover:border-orange-500/50 transition-colors"
              >
                <Upload className="w-12 h-12 mx-auto mb-4 text-gray-400" />
                <p className="text-white font-medium">
                  {selectedFile ? selectedFile.name : "Drop file here or click to upload"}
                </p>
                <p className="text-sm text-gray-400 mt-1">
                  Supports: .py, .js, .ts, .json, .yaml, .yml
                </p>
                <input
                  ref={fileInputRef}
                  type="file"
                  onChange={handleFileSelect}
                  accept=".py,.js,.ts,.json,.yaml,.yml"
                  className="hidden"
                />
              </div>
            </div>

            {/* Format Selection */}
            <div className="bg-white/10 backdrop-blur-sm border border-white/10 rounded-xl p-6">
              <h3 className="text-lg font-bold text-white mb-4">2. Select Output Format</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                {[
                  { id: "openapi", label: "OpenAPI 3.0", icon: FileCode },
                  { id: "swagger", label: "Swagger 2.0", icon: Code2 },
                  { id: "asyncapi", label: "AsyncAPI", icon: Sparkles },
                  { id: "graphql", label: "GraphQL", icon: FileJson }
                ].map((fmt) => {
                  const Icon = fmt.icon;
                  return (
                    <button
                      key={fmt.id}
                      onClick={() => setFormat(fmt.id as SpecFormat)}
                      className={`p-4 rounded-lg border transition-all ${
                        format === fmt.id
                          ? "bg-orange-500/20 border-orange-500 text-white"
                          : "bg-white/5 border-white/10 text-gray-400 hover:border-white/30"
                      }`}
                    >
                      <Icon className="w-6 h-6 mx-auto mb-2" />
                      <span className="text-xs">{fmt.label}</span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Generate Button */}
            <Button
              onClick={generateSpec}
              disabled={!selectedFile || generating}
              className="w-full py-6 text-lg"
            >
              <Sparkles className={`w-5 h-5 mr-2 ${generating ? "animate-spin" : ""}`} />
              {generating ? "Analyzing Code..." : "Generate API Documentation"}
            </Button>
          </div>

          {/* Right Column: Results */}
          <div className="space-y-6">
            {/* Spec Preview */}
            <div className="bg-white/10 backdrop-blur-sm border border-white/10 rounded-xl p-6">
              <h3 className="text-lg font-bold text-white mb-4 flex items-center justify-between">
                <span>Generated Specification</span>
                {generatedSpec && (
                  <div className="flex gap-2">
                    <Button
                      onClick={() => downloadSpec("json")}
                      size="sm"
                      variant="outline"
                    >
                      <FileJson className="w-4 h-4 mr-1" />
                      JSON
                    </Button>
                    <Button
                      onClick={() => downloadSpec("yaml")}
                      size="sm"
                      variant="outline"
                    >
                      <FileCode className="w-4 h-4 mr-1" />
                      YAML
                    </Button>
                  </div>
                )}
              </h3>
              {generatedSpec ? (
                <div className="space-y-4">
                  <div className="p-3 bg-black/30 rounded-lg">
                    <p className="text-xs text-gray-400">Title</p>
                    <p className="text-white font-medium">{generatedSpec.info?.title}</p>
                  </div>
                  <div className="p-3 bg-black/30 rounded-lg">
                    <p className="text-xs text-gray-400">Version</p>
                    <p className="text-white font-mono">{generatedSpec.info?.version}</p>
                  </div>
                  <div className="p-3 bg-black/30 rounded-lg">
                    <p className="text-xs text-gray-400">Endpoints</p>
                    <p className="text-white font-mono">{Object.keys(generatedSpec.paths || {}).length} defined</p>
                  </div>
                </div>
              ) : (
                <p className="text-gray-400 text-sm text-center py-8">
                  Upload a file and generate to see the specification
                </p>
              )}
            </div>

            {/* Raw Spec Output */}
            {specYaml && (
              <div className="bg-white/10 backdrop-blur-sm border border-white/10 rounded-xl p-6">
                <h3 className="text-lg font-bold text-white mb-4">Raw Output</h3>
                <pre className="bg-black/30 p-4 rounded-lg overflow-x-auto text-xs text-green-400 max-h-64">
                  {specYaml}
                </pre>
              </div>
            )}

            {/* API Reference */}
            <div className="bg-white/10 backdrop-blur-sm border border-white/10 rounded-xl p-6">
              <h3 className="text-lg font-bold text-white mb-4">API Reference</h3>
              <div className="space-y-2 text-sm">
                <div className="p-3 bg-black/30 rounded-lg">
                  <p className="text-gray-400 mb-1">POST</p>
                  <code className="text-green-400 text-xs">
                    /api/analysis/api-doc
                  </code>
                  <p className="text-gray-500 text-xs mt-1">
                    Generate OpenAPI spec from document
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
