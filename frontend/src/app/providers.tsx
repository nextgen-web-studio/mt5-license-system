'use client';

import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import React, { useState, createContext, useContext, useCallback } from 'react';
import { AlertCircle, CheckCircle, Info, X } from 'lucide-react';

type ToastType = 'success' | 'error' | 'info';

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
        staleTime: 60 * 1000,
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
          <div className="fixed bottom-6 right-6 z-[9999] animate-in slide-in-from-bottom-5 fade-in duration-300">
            <div className={lex items-center gap-3 px-4 py-3 rounded-xl shadow-2xl border  backdrop-blur-md}>
              {toastState.type === 'error' && <AlertCircle size={20} className="text-red-500" />}
              {toastState.type === 'success' && <CheckCircle size={20} className="text-emerald-500" />}
              {toastState.type === 'info' && <Info size={20} className="text-blue-500" />}
              <span className="text-sm font-medium max-w-sm whitespace-pre-wrap">{toastState.message}</span>
              <button onClick={() => setToastState(p => ({ ...p, visible: false }))} className="ml-2 hover:opacity-70">
                <X size={16} />
              </button>
            </div>
          </div>
        )}
      </ToastContext.Provider>
    </QueryClientProvider>
  );
}
