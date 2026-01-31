"use client";
import ArtifactsPanel from '@/components/ArtifactsPanel';

export default function ArtifactsPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-white mb-8">Artifacts Explorer</h1>
      <div className="bg-gray-900 rounded-xl p-6 border border-gray-800 shadow-lg">
        <ArtifactsPanel />
      </div>
    </div>
  );
}
