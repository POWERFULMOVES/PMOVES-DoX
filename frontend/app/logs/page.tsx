"use client";
import LogsPanel from '@/components/LogsPanel';

export default function LogsPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-white mb-8">System Logs</h1>
      <div className="bg-gray-900 rounded-xl p-6 border border-gray-800 shadow-lg">
        <LogsPanel />
      </div>
    </div>
  );
}
