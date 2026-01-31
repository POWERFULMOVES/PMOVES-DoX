"use client";
import TagsPanel from '@/components/TagsPanel';

export default function TagsPage() {
  return (
    <div className="space-y-6">
      <h1 className="text-3xl font-bold text-white mb-8">Tags & Metadata</h1>
      <div className="bg-gray-900 rounded-xl p-6 border border-gray-800 shadow-lg">
        <TagsPanel />
      </div>
    </div>
  );
}
