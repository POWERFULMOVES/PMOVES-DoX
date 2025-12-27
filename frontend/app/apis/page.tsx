"use client";
import APIsPanel from '@/components/APIsPanel';

export default function APIsPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-white mb-8">API Catalog</h1>
      <div className="bg-gray-900 rounded-xl p-6 border border-gray-800 shadow-lg">
        <APIsPanel />
      </div>
    </div>
  );
}
