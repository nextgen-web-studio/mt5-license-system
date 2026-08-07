'use client';

import { useQuery } from '@tanstack/react-query';
import { Key, Shield, ShieldAlert, Loader2, Copy } from 'lucide-react';
import api from '@/lib/api';

export default function LicensesPage() {
  const { data: licenses = [], isLoading, error } = useQuery({
    queryKey: ['admin-licenses'],
    queryFn: async () => {
      const { data } = await api.get('/api/v1/admin/licenses');
      return data;
    }
  });

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="animate-spin text-blue-500" size={32} />
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-500/10 border border-red-500/20 text-red-400 p-4 rounded-lg">
        Failed to load licenses.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Licenses</h1>
          <p className="text-neutral-400 mt-1">Manage active MT4/MT5 product licenses.</p>
        </div>
      </div>

      <div className="bg-neutral-900 border border-neutral-800 rounded-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead className="text-xs text-neutral-400 bg-neutral-900/50 uppercase border-b border-neutral-800">
              <tr>
                <th className="px-6 py-4">License Key</th>
                <th className="px-6 py-4">Customer</th>
                <th className="px-6 py-4">MT4/MT5 ID</th>
                <th className="px-6 py-4">Status</th>
                <th className="px-6 py-4">Generated On</th>
                <th className="px-6 py-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-800">
              {licenses.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-6 py-8 text-center text-neutral-500">
                    No licenses found.
                  </td>
                </tr>
              ) : (
                licenses.map((license: any) => (
                  <tr key={license.id} className="hover:bg-neutral-800/30 transition-colors">
                    <td className="px-6 py-4 font-mono text-xs text-neutral-300 flex items-center space-x-2">
                      <Key size={14} className="text-indigo-400" />
                      <span>{license.id || license.key}</span>
                    </td>
                    <td className="px-6 py-4 text-neutral-400">{license.customer || 'Guest'}</td>
                    <td className="px-6 py-4 font-mono text-xs text-white">{license.mt5_id || 'N/A'}</td>
                    <td className="px-6 py-4">
                      {license.status === 'active' || license.status === 'valid' ? (
                        <span className="flex items-center space-x-1 text-emerald-400 text-xs font-medium">
                          <Shield size={14} />
                          <span>Active</span>
                        </span>
                      ) : (
                        <span className="flex items-center space-x-1 text-red-400 text-xs font-medium">
                          <ShieldAlert size={14} />
                          <span>{license.status || 'Expired'}</span>
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-neutral-400">
                      {new Date(license.created_at || Date.now()).toLocaleDateString()}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <button 
                        onClick={() => copyToClipboard(license.id || license.key)}
                        className="p-2 text-neutral-400 hover:text-white hover:bg-neutral-700 rounded transition-colors"
                        title="Copy Key"
                      >
                        <Copy size={16} />
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
