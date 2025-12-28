"use client";

import { HyperbolicNavigator } from "@/components/geometry/HyperbolicNavigator";
import { ErrorBoundary } from "@/components/ErrorBoundary";

const initialData = {
  super_nodes: [
    {
      id: "root",
      label: "Waiting for Data...",
      x: 0,
      y: 0,
      r: 20,
      constellations: []
    }
  ]
};

export default function GeometryPage() {
  return (
    <div className="flex flex-col h-screen bg-slate-950 text-white">
        <header className="p-4 border-b border-slate-800">
            <h1 className="text-xl font-bold">Geometric Intelligence / Shape Discovery</h1>
        </header>
        <main className="flex-1 p-4 relative">
             <ErrorBoundary>
                 <HyperbolicNavigator 
                    data={initialData} 
                    width={1200} 
                    height={800} 
                    className="w-full h-full shadow-2xl shadow-blue-900/20"
                 />
             </ErrorBoundary>
        </main>
    </div>
  );
}
