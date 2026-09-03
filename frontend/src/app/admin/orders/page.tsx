'use client';

import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Loader2, Trash2 } from 'lucide-react';
import api from '@/lib/api';
import { useToast } from '@/app/providers';
import ConfirmModal from '@/components/ui/ConfirmModal';
import { useState } from 'react';

const currencyFormatter = new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 });

export default function OrdersPage() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [deletingId, setDeletingId] = useState<number | string | null>(null);

  const { data: orders = [], isLoading, error } = useQuery({
    
    queryKey: ['admin-orders'],
    refetchInterval: 2000,
    refetchIntervalInBackground: true,
    queryFn: async () => {
      const { data } = await api.get('/api/v1/admin/all_orders');
      return data;
    }
  });

  const getStatusBadge = (status: string) => {
    switch (status?.toLowerCase()) {
      case 'paid':
      case 'approved':
      case 'delivered':
      case 'provisioned':
        return <span className="px-2 py-1 bg-emerald-500/10 text-emerald-400 rounded text-xs font-medium border border-emerald-500/20">{status}</span>;
      case 'pending':
      case 'pending_admin_approval':
        return <span className="px-2 py-1 bg-yellow-500/10 text-yellow-400 rounded text-xs font-medium border border-yellow-500/20">{status}</span>;
      case 'contacted':
        return <span className="px-2 py-1 bg-blue-500/10 text-blue-400 rounded text-xs font-medium border border-blue-500/20">{status}</span>;
      case 'compiling':
      case 'generating':
        return <span className="px-2 py-1 bg-purple-500/10 text-purple-400 rounded text-xs font-medium border border-purple-500/20">{status}</span>;
      case 'failed':
      case 'rejected':
        return <span className="px-2 py-1 bg-red-500/10 text-red-400 rounded text-xs font-medium border border-red-500/20">{status}</span>;
      default:
        return <span className="px-2 py-1 bg-neutral-500/10 text-neutral-400 rounded text-xs font-medium border border-neutral-500/20">{status || 'Unknown'}</span>;
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="animate-spin text-blue-500" size={32} />
      </div>
    );
  }

  if (error && (!orders || (Array.isArray(orders) && orders.length === 0) || (typeof orders === 'object' && Object.keys(orders).length === 0))) {
    return (
      <div className="bg-red-500/10 border border-red-500/20 text-red-400 p-4 rounded-lg">
        Failed to load orders.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Orders</h1>
          <p className="text-neutral-400 mt-1">Manage and view all customer orders.</p>
        </div>
      </div>

        <div className="bg-neutral-900 border border-neutral-800 rounded-xl">
          {/* Desktop Table */}
          <div className="hidden md:block overflow-x-auto min-h-[300px]">
            <table className="min-w-full text-sm text-left">
              <thead className="text-xs text-neutral-400 bg-neutral-900/50 uppercase border-b border-neutral-800">
                <tr>
                  <th className="px-6 py-4 whitespace-nowrap">Order ID</th>
                  <th className="px-3 py-2 md:px-6 md:py-4">Product</th>
                  <th className="px-3 py-2 md:px-6 md:py-4">Customer</th>
                  <th className="px-3 py-2 md:px-6 md:py-4">Amount (INR)</th>
                  <th className="px-6 py-4 whitespace-nowrap">Status</th>
                  <th className="px-3 py-2 md:px-6 md:py-4">Date</th>
                  <th className="px-6 py-4 text-right whitespace-nowrap">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-neutral-800">
                {orders.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="px-6 py-8 text-center text-neutral-500">
                      No orders found.
                    </td>
                  </tr>
                ) : (
                  orders.map((order: any) => (
                    <tr key={order.id} className="hover:bg-neutral-800/30 transition-colors">
                      <td className="px-3 py-2 md:px-6 md:py-4 font-medium text-neutral-300 whitespace-nowrap">#{order.id}</td>
                      <td className="px-3 py-2 md:px-6 md:py-4 text-white">{order.product || 'Unknown'}</td>
                      <td className="px-3 py-2 md:px-6 md:py-4 text-neutral-400">{order.customer || 'Guest'}</td>
                        <td className="px-3 py-2 md:px-6 md:py-4 text-neutral-300">{currencyFormatter.format(order.amount || 0)}</td>
                      <td className="px-3 py-2 md:px-6 md:py-4">{getStatusBadge(order.status)}</td>
                      <td className="px-3 py-2 md:px-6 md:py-4 text-neutral-400 whitespace-nowrap">{new Date(order.date || Date.now()).toLocaleString('en-GB', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit', hour12: false })}</td>
                      <td className="px-6 py-4 text-right">
                        <button 
                          onClick={() => { setDeletingId(order.id); setDeleteModalOpen(true); }}
                          className="p-2 text-neutral-400 hover:text-red-500 hover:bg-red-500/10 rounded transition-colors" title="Delete Order">
                          <Trash2 size={16} />
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Mobile Card Layout */}
          <div className="md:hidden flex flex-col divide-y divide-neutral-800">
            {orders.length === 0 ? (
              <div className="p-8 text-center text-neutral-500">No orders found.</div>
            ) : (
              orders.map((order: any) => (
                  <div key={order.id} className="p-3 space-y-2">
                    <div className="flex justify-between items-start">
                      <span className="font-medium text-white text-xs">#{order.id}</span>
                      {getStatusBadge(order.status)}
                    </div>
                    <div className="flex justify-between text-xs">
                      <span className="text-neutral-500">Product</span>
                      <span className="text-white text-right font-medium">{order.product || 'Unknown'}</span>
                    </div>
                    <div className="flex justify-between text-xs">
                      <span className="text-neutral-500">Customer</span>
                      <span className="text-neutral-300 text-right">{order.customer || 'Guest'}</span>
                    </div>
                    <div className="flex justify-between text-xs">
                      <span className="text-neutral-500">Amount</span>
                      <span className="text-neutral-300 text-right">{currencyFormatter.format(order.amount || 0)}</span>
                    </div>
                    <div className="flex justify-between text-xs items-center pt-1 border-t border-neutral-800/50">
                      <span className="text-neutral-500 text-[10px]">{new Date(order.date || Date.now()).toLocaleString('en-GB', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit', hour12: false })}</span>
                      <button 
                        onClick={() => { setDeletingId(order.id); setDeleteModalOpen(true); }}
                        className="p-1.5 text-neutral-400 hover:text-red-500 hover:bg-red-500/10 rounded transition-colors" title="Delete Order">
                        <Trash2 size={14} />
                      </button>
                    </div>
                  </div>
              ))
            )}
          </div>
        </div>
    
      <ConfirmModal
        isOpen={deleteModalOpen}
        title="Delete Order"
        message="Are you sure you want to permanently delete this order? This action cannot be undone."
        confirmText="Delete"
        cancelText="Cancel"
        onConfirm={async () => {
          if(!deletingId) return;
          const targetId = deletingId;
          setDeleteModalOpen(false);
          setDeletingId(null);
          try {
            // Optimistic UI update for instant response
            queryClient.setQueryData(['admin-orders'], (old: any) => old?.filter((item: any) => item.id !== targetId));
            await api.delete(`/api/v1/orders/${targetId}`);
            queryClient.invalidateQueries({ queryKey: ['admin-orders'] });
          } catch(e) {
            toast('Failed to delete. Make sure your API is fully deployed!', 'error');
          }
        }}
        onCancel={() => {
          setDeleteModalOpen(false);
          setDeletingId(null);
        }}
      />
    
</div>
  );
}

