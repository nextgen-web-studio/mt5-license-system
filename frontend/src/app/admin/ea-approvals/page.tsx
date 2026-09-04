'use client';

import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Check, X, ShieldCheck, CreditCard, Loader2 } from 'lucide-react';
import api from '@/lib/api';
import { useToast } from '@/app/providers';
import { useRouter } from 'next/navigation';

export default function EaApprovalsPage() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const router = useRouter();

  const [approveModalOpen, setApproveModalOpen] = useState(false);
  const [selectedOrder, setSelectedOrder] = useState<any>(null);

  const { data: orders = [], isLoading, error } = useQuery({
    queryKey: ['admin-ea-orders'],
    refetchInterval: 5000,
    queryFn: async () => {
      const { data } = await api.get('/api/v1/admin/all_orders');
      return data.filter((o: any) => o.product?.includes('EA'));
    }
  });

  const getStatusBadge = (status: string) => {
    const formattedStatus = (status || 'Unknown').replace(/_/g, ' ');
    switch (status?.toLowerCase()) {
      case 'paid':
      case 'approved':
      case 'delivered':
      case 'provisioned':
        return <span className="px-2 py-1 bg-emerald-500/10 text-emerald-400 rounded text-xs font-medium border border-emerald-500/20 capitalize whitespace-nowrap">{formattedStatus}</span>;
      case 'pending':
      case 'pending_admin_approval':
      case 'approved_waiting_for_mt5_id':
        return <span className="px-2 py-1 bg-yellow-500/10 text-yellow-400 rounded text-xs font-medium border border-yellow-500/20 capitalize whitespace-nowrap">{formattedStatus}</span>;
      case 'compiling':
      case 'generating':
        return <span className="px-2 py-1 bg-purple-500/10 text-purple-400 rounded text-xs font-medium border border-purple-500/20 capitalize whitespace-nowrap">{formattedStatus}</span>;
      case 'failed':
      case 'rejected':
        return <span className="px-2 py-1 bg-red-500/10 text-red-400 rounded text-xs font-medium border border-red-500/20 capitalize whitespace-nowrap">{formattedStatus}</span>;
      default:
        return <span className="px-2 py-1 bg-neutral-500/10 text-neutral-400 rounded text-xs font-medium border border-neutral-500/20 capitalize whitespace-nowrap">{formattedStatus}</span>;
    }
  };

  const generateMutation = useMutation({
    mutationFn: async (order: any) => {
      const { data } = await api.post(`/api/v1/licenses/generate`, {
        order_id: order.id,
        mt5_id: order.mt5_id
      });
      return data;
    },
    onSuccess: () => {
      toast("Lifetime License Generated & Compiling!", "success");
      setApproveModalOpen(false);
      queryClient.invalidateQueries({ queryKey: ['admin-ea-orders'] });
    },
    onError: (err: any) => {
      toast("Error generating license: " + (err.response?.data?.detail || err.message), "error");
    }
  });

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
        Failed to load EA orders.
      </div>
    );
  }

  const pendingOrders = orders.filter((o: any) => o.status === 'pending_admin_approval' || o.status === 'approved_waiting_for_mt5_id' || o.status === 'approved');
  const otherOrders = orders.filter((o: any) => o.status !== 'pending_admin_approval' && o.status !== 'approved_waiting_for_mt5_id' && o.status !== 'approved');

  const renderTable = (tableOrders: any[]) => (
    <div className="overflow-x-auto">
      <table className="min-w-full text-sm text-left">
        <thead className="text-xs text-neutral-400 bg-neutral-900/50 uppercase border-b border-neutral-800">
          <tr>
            <th className="px-6 py-4 whitespace-nowrap">Order ID</th>
            <th className="px-6 py-4">Product</th>
            <th className="px-6 py-4">Customer</th>
            <th className="px-6 py-4">MT5 ID</th>
            <th className="px-6 py-4">Status</th>
            <th className="px-6 py-4">Date</th>
            <th className="px-6 py-4 text-right">Actions</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-neutral-800">
          {tableOrders.length === 0 ? (
            <tr>
              <td colSpan={7} className="px-6 py-8 text-center text-neutral-500">No EA orders found.</td>
            </tr>
          ) : (
            tableOrders.map((order: any) => (
              <tr key={order.id} className="hover:bg-neutral-800/30 transition-colors">
                <td className="px-6 py-4 font-medium text-neutral-300 whitespace-nowrap">#{order.id}</td>
                <td className="px-6 py-4 text-white whitespace-nowrap">
                  <span className="flex items-center gap-2">
                    {order.product || 'Unknown'}
                  </span>
                </td>
                <td className="px-6 py-4 text-neutral-400">{order.customer || 'Guest'}</td>
                <td className="px-6 py-4 font-mono text-xs text-neutral-400">{order.mt5_id || 'N/A'}</td>
                <td className="px-6 py-4">{getStatusBadge(order.status)}</td>
                <td className="px-6 py-4 text-neutral-400 whitespace-nowrap">{new Date(order.date || Date.now()).toLocaleDateString('en-GB')}</td>
                <td className="px-6 py-4 text-right">
                  {(order.status === 'pending_admin_approval' || order.status === 'approved' || order.status === 'approved_waiting_for_mt5_id') && (
                    <button 
                      onClick={() => {
                        setSelectedOrder(order);
                        setApproveModalOpen(true);
                      }}
                      className="px-3 py-1.5 text-xs font-medium text-emerald-400 hover:text-emerald-300 bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/20 rounded-lg transition-colors"
                    >
                      Process Approval
                    </button>
                  )}
                </td>
              </tr>
            ))
          )}
        </tbody>
      </table>
    </div>
  );

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-white mb-2">EA Approvals</h1>
        <p className="text-neutral-400">Manage, approve, and provision Infinity Trader EA licenses.</p>
      </div>

      <div className="bg-neutral-900 border border-neutral-800 rounded-xl overflow-hidden">
        <div className="px-6 py-4 border-b border-neutral-800 bg-neutral-900/50">
          <h2 className="text-sm font-semibold text-white">Pending Action</h2>
        </div>
        {renderTable(pendingOrders)}
      </div>

      <div className="bg-neutral-900 border border-neutral-800 rounded-xl overflow-hidden opacity-80">
        <div className="px-6 py-4 border-b border-neutral-800 bg-neutral-900/50">
          <h2 className="text-sm font-semibold text-neutral-300">History</h2>
        </div>
        {renderTable(otherOrders)}
      </div>

      {approveModalOpen && selectedOrder && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-neutral-900 border border-neutral-800 rounded-xl w-full max-w-md shadow-2xl overflow-hidden">
            <div className="px-6 py-4 border-b border-neutral-800 flex items-center justify-between">
              <h3 className="text-lg font-bold text-white flex items-center">
                <ShieldCheck size={18} className="mr-2 text-emerald-400" />
                Process EA Approval
              </h3>
              <button 
                onClick={() => setApproveModalOpen(false)}
                className="text-neutral-500 hover:text-white transition-colors"
              >
                <X size={20} />
              </button>
            </div>
            
            <div className="p-6 space-y-4">
              <div className="bg-neutral-950 p-4 rounded-lg border border-neutral-800 text-sm space-y-2">
                <div className="flex justify-between">
                  <span className="text-neutral-400">Order ID:</span>
                  <span className="text-white font-medium">#{selectedOrder.id}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-neutral-400">Customer:</span>
                  <span className="text-white font-medium">{selectedOrder.customer}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-neutral-400">MT5 ID:</span>
                  <span className="text-white font-mono">{selectedOrder.mt5_id || 'Not Provided'}</span>
                </div>
              </div>

              {!selectedOrder.mt5_id ? (
                <div className="p-4 bg-yellow-500/10 border border-yellow-500/20 rounded-lg text-yellow-400 text-sm text-center">
                  Cannot process license until customer provides their MT5 ID.
                </div>
              ) : (
                <div className="space-y-3">
                  <p className="text-sm text-neutral-300 text-center mb-4">How would you like to process this EA?</p>
                  
                  <button
                    disabled={generateMutation.isPending}
                    onClick={() => generateMutation.mutate(selectedOrder)}
                    className="w-full flex items-center justify-center p-3 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg font-medium transition-colors disabled:opacity-50"
                  >
                    {generateMutation.isPending ? (
                      <Loader2 size={18} className="animate-spin" />
                    ) : (
                      <>
                        <ShieldCheck size={18} className="mr-2" />
                        Generate Lifetime License
                      </>
                    )}
                  </button>

                  <div className="relative flex items-center py-2">
                    <div className="flex-grow border-t border-neutral-800"></div>
                    <span className="flex-shrink-0 mx-4 text-xs text-neutral-500 uppercase">Or</span>
                    <div className="flex-grow border-t border-neutral-800"></div>
                  </div>

                  <button
                    onClick={() => {
                      setApproveModalOpen(false);
                      router.push('/admin/installments');
                    }}
                    className="w-full flex items-center justify-center p-3 bg-neutral-800 hover:bg-neutral-700 text-white border border-neutral-700 rounded-lg font-medium transition-colors"
                  >
                    <CreditCard size={18} className="mr-2" />
                    Create Installment Arrangement
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
