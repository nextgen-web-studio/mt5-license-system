'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React, { useState, createContext, useContext, useCallback } from 'react';
import { AlertCircle, CheckCircle, Info, X, Trash2 } from 'lucide-react';

type ToastType = 'success' | 'error' | 'info' | 'delete';

interface ToastContextType {
  toast: (message: string, type?: ToastType) => void;
}

const ToastContext = createContext<ToastContextType | undefined>(undefined);

export function useToast() {
  const context = useContext(ToastContext);
  if (!context) throw new Error('useToast must be used within ToastProvider');
  return context;
}

export function Providers({ children }: { children: React.ReactNode }) {
  const [queryClient] = useState(() => new QueryClient({
    defaultOptions: {
      queries: {
        staleTime: 5 * 60 * 1000,
        gcTime: 10 * 60 * 1000,
        retry: 2,
        retryDelay: 500,
        refetchOnWindowFocus: true,
      },
    },
  }));

  const [toastState, setToastState] = useState<{ message: string; type: ToastType; visible: boolean; id: number }>({
    message: '',
    type: 'info',
    visible: false,
    id: 0
  });

  const toast = useCallback((message: string, type: ToastType = 'info') => {
    const id = Date.now();
    setToastState({ message, type, visible: true, id });
    setTimeout(() => {
      setToastState(prev => (prev.id === id ? { ...prev, visible: false } : prev));
    }, 4000);
  }, []);

  return (
    <QueryClientProvider client={queryClient}>
      <ToastContext.Provider value={{ toast }}>
        {children}
        
        {toastState.visible && (
            <div className="fixed z-[9999] animate-in slide-in-from-top-5 fade-in duration-300 top-4 right-4 sm:top-6 sm:right-6 w-auto max-w-[90vw]">
              <div className={`flex items-center gap-3 px-4 py-3 rounded-2xl shadow-2xl border ${
                toastState.type === 'error' ? 'bg-red-950/90 border-red-900/50 text-red-200' :
                toastState.type === 'delete' ? 'bg-red-950/90 border-red-900/50 text-red-200' :
                toastState.type === 'success' ? 'bg-emerald-950/90 border-emerald-900/50 text-emerald-200' :
                'bg-neutral-900/90 border-neutral-800 text-neutral-200'
              } backdrop-blur-md`}>
                {toastState.type === 'error' && <AlertCircle size={20} className="text-red-500 shrink-0" />}
                {toastState.type === 'delete' && <Trash2 size={20} className="text-red-500 shrink-0" />}
                {toastState.type === 'success' && <CheckCircle size={20} className="text-emerald-500 shrink-0" />}
                {toastState.type === 'info' && <Info size={20} className="text-blue-500 shrink-0" />}
                <span className="text-sm font-medium whitespace-pre-wrap">{toastState.message}</span>
                <button onClick={() => setToastState(p => ({ ...p, visible: false }))} className="ml-1 shrink-0 hover:opacity-70">
                  <X size={16} />
                </button>
              </div>
            </div>
          )}
      </ToastContext.Provider>
    </QueryClientProvider>
  );
}
