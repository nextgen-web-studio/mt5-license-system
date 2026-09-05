'use client';

import { useQuery, keepPreviousData} from '@tanstack/react-query';
import { Terminal, RefreshCcw, Loader2, CheckCircle2, XCircle } from 'lucide-react';
import api from '@/lib/api';

export default function CompilerPage() {
  const { data: compilerJobs = [], isLoading, isFetching, error, refetch } = useQuery({
    
    queryKey: ['admin-compiler-jobs'],
    refetchInterval: 5000,
    refetchIntervalInBackground: true,
      placeholderData: keepPreviousData,
    queryFn: async () => {
      const { data } = await api.get('/api/v1/admin/compiler_jobs');
      return data;
    }
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="animate-spin text-blue-500" size={32} />
      </div>
    );
  }

  if (error && (!compilerJobs || (Array.isArray(compilerJobs) && compilerJobs.length === 0) || (typeof compilerJobs === 'object' && Object.keys(compilerJobs).length === 0))) {
    return (
      <div className="bg-red-500/10 border border-red-500/20 text-red-400 p-4 rounded-lg">
        Failed to load compiler jobs.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Compiler Workers</h1>
          <p className="text-neutral-400 mt-1">Monitor automated EA compilation jobs.</p>
        </div>
        <button 
          onClick={() => refetch()}
          className="flex items-center px-4 py-2 bg-neutral-800 hover:bg-neutral-700 text-white rounded-lg font-medium transition-colors"
        >
          <RefreshCcw size={18} className="mr-2" />
          Refresh
        </button>
      </div>

      {/* Desktop Table */}
      <div className="bg-neutral-900 border border-neutral-800 rounded-xl">
        <div className="hidden md:block overflow-x-auto min-h-[300px]">
          <table className="min-w-full text-sm text-left">
            <thead className="text-xs text-neutral-400 bg-neutral-900/50 uppercase border-b border-neutral-800">
              <tr>
                <th className="px-6 py-4 whitespace-nowrap">Job ID</th>
                <th className="px-6 py-4 whitespace-nowrap">Order ID</th>
                <th className="px-6 py-4">Status</th>
                <th className="px-6 py-4">Logs</th>
                <th className="px-6 py-4 text-right whitespace-nowrap">Timestamp</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-800">
              {compilerJobs.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-6 py-8 text-center text-neutral-500">
                    No active or recent compiler jobs.
                  </td>
                </tr>
              ) : (
                compilerJobs.map((job: any) => (
                  <tr key={job.id} className="hover:bg-neutral-800/30 transition-colors">
                    <td className="px-6 py-4 font-mono text-xs text-neutral-300 whitespace-nowrap">
                      <span className="inline-flex items-center space-x-2">
                        <Terminal size={14} className="text-blue-400" />
                        <span>{job.id}</span>
                      </span>
                    </td>
                    <td className="px-6 py-4 text-neutral-400 whitespace-nowrap">#{job.order_id}</td>
                    <td className="px-6 py-4">
                      {job.status === 'completed' ? (
                        <span className="flex items-center space-x-1 text-emerald-400 text-xs font-medium">
                          <CheckCircle2 size={14} /><span>Completed</span>
                        </span>
                      ) : job.status === 'failed' ? (
                        <span className="flex items-center space-x-1 text-red-400 text-xs font-medium">
                          <XCircle size={14} /><span>Failed</span>
                        </span>
                      ) : (
                        <span className="flex items-center space-x-1 text-yellow-400 text-xs font-medium">
                          <Loader2 size={14} className="animate-spin" /><span className="capitalize">{job.status || 'Pending'}</span>
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4 text-neutral-400 text-xs max-w-xs truncate" title={job.error_message || job.logs || ''}>
                      {job.error_message ? job.error_message : job.status === 'completed' ? 'Completed successfully' : job.logs || 'No logs available'}
                    </td>
                    <td className="px-6 py-4 text-right text-neutral-400 whitespace-nowrap">
                      {new Date(job.created_at || Date.now()).toLocaleString('en-GB', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit', hour12: false })}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {/* Mobile Card Layout */}
        <div className="md:hidden flex flex-col divide-y divide-neutral-800">
          {compilerJobs.length === 0 ? (
            <div className="p-8 text-center text-neutral-500">No active or recent compiler jobs.</div>
          ) : (
            compilerJobs.map((job: any) => (
              <div key={job.id} className="p-3 space-y-2">
                <div className="flex justify-between items-center">
                  <span className="inline-flex items-center gap-1.5 font-mono text-xs text-blue-400">
                    <Terminal size={12} />
                    Job #{job.id}
                  </span>
                  {job.status === 'completed' ? (
                    <span className="flex items-center gap-1 text-emerald-400 text-xs font-medium">
                      <CheckCircle2 size={13} /> Completed
                    </span>
                  ) : job.status === 'failed' ? (
                    <span className="flex items-center gap-1 text-red-400 text-xs font-medium">
                      <XCircle size={13} /> Failed
                    </span>
                  ) : (
                    <span className="flex items-center gap-1 text-yellow-400 text-xs font-medium">
                      <Loader2 size={13} className="animate-spin" />
                      <span className="capitalize">{job.status || 'Pending'}</span>
                    </span>
                  )}
                </div>
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div>
                    <span className="text-neutral-500 block text-[10px] mb-0.5">Order ID</span>
                    <span className="text-neutral-300">#{job.order_id}</span>
                  </div>
                  <div>
                    <span className="text-neutral-500 block text-[10px] mb-0.5">Time</span>
                    <span className="text-neutral-400">{new Date(job.created_at || Date.now()).toLocaleString('en-GB', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit', hour12: false })}</span>
                  </div>
                </div>
                {(job.error_message || job.logs) && (
                  <div className="text-[10px] text-neutral-500 bg-neutral-800/50 rounded px-2 py-1 truncate">
                    {job.error_message || job.logs}
                  </div>
                )}
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}
