"use client";

import React, { createContext, useCallback, useContext, useMemo, useState } from 'react';

type Toast = { id: string; message: string; type?: 'info'|'success'|'error'};

type ToastCtx = {
  push: (msg: string, type?: Toast['type']) => void;
};

const Ctx = createContext<ToastCtx | null>(null);

export function ToastProvider({ children }: { children: React.ReactNode }) {
  const [items, setItems] = useState<Toast[]>([]);
  const push = useCallback((message: string, type: Toast['type'] = 'info') => {
    const id = Math.random().toString(36).slice(2);
    setItems(prev => [...prev, { id, message, type }]);
    setTimeout(() => setItems(prev => prev.filter(t => t.id !== id)), 3500);
  }, []);
  const value = useMemo(()=>({ push }),[push]);
  return (
    <Ctx.Provider value={value}>
      {children}
      <div className="fixed bottom-4 right-4 z-50 space-y-2">
        {items.map(t => (
          <div key={t.id} className={`px-3 py-2 rounded shadow text-sm text-white ${t.type==='success'?'bg-green-600':t.type==='error'?'bg-red-600':'bg-gray-800'}`}>
            {t.message}
          </div>
        ))}
      </div>
    </Ctx.Provider>
  );
}

export function useToast() {
  const ctx = useContext(Ctx);
  if (!ctx) throw new Error('useToast must be used within ToastProvider');
  return ctx;
}

export function ToastViewport() { return null; }

