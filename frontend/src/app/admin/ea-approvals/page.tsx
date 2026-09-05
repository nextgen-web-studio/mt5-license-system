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
  const [installmentMode, setInstallmentMode] = useState(false);
  const [totalAmount, setTotalAmount] = useState('');
  const [installmentAmount, setInstallmentAmount] = useState('');
  const [installmentCount, setInstallmentCount] = useState('');
  const [firstPayment, setFirstPayment] = useState('');
  const [licenseDays, setLicenseDays] = useState('30');

  const { data: orders = [], isLoading, error } = useQuery({
    queryKey: ['admin-ea-orders'],
    refetchInterval: 15000,
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
      case 'pending_broker_change_approval':
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

  const createInstallmentMutation = useMutation({
    mutationFn: async () => {
      if (selectedOrder.status === 'pending_admin_approval') {
        await api.post(`/api/v1/orders/${selectedOrder.id}/approve`);
      }
      const { data } = await api.post(`/api/v1/installments/create`, {
        order_id: selectedOrder.id,
        total_amount: parseFloat(totalAmount),
        installment_amount: parseFloat(installmentAmount),
        installment_count: parseInt(installmentCount, 10),
        first_payment_amount: parseFloat(firstPayment || installmentAmount),
        license_period_days: parseInt(licenseDays, 10)
      });
      return data;
    },
    onSuccess: () => {
      toast("Installment arrangement created successfully!", "success");
      setApproveModalOpen(false);
      setInstallmentMode(false);
      queryClient.invalidateQueries({ queryKey: ['admin-ea-orders'] });
    },
    onError: (err: any) => {
      toast("Error creating installment: " + (err.response?.data?.detail || err.message), "error");
    }
  });

  const approveBrokerChangeMutation = useMutation({
    mutationFn: async (order: any) => {
      const { data } = await api.post(`/api/v1/licenses/broker-change/${order.real_id}/approve`);
      return data;
    },
    onSuccess: () => {
      toast("Broker Change Approved & Compiling!", "success");
      setApproveModalOpen(false);
      queryClient.invalidateQueries({ queryKey: ['admin-ea-orders'] });
    },
    onError: (err: any) => {
      toast("Error approving broker change: " + (err.response?.data?.detail || err.message), "error");
    }
  });

  const rejectBrokerChangeMutation = useMutation({
    mutationFn: async (order: any) => {
      const { data } = await api.post(`/api/v1/licenses/broker-change/${order.real_id}/reject`);
      return data;
    },
    onSuccess: () => {
      toast("Broker Change Rejected", "success");
      setApproveModalOpen(false);
      queryClient.invalidateQueries({ queryKey: ['admin-ea-orders'] });
    },
    onError: (err: any) => {
      toast("Error rejecting broker change: " + (err.response?.data?.detail || err.message), "error");
    }
  });

  const generateMutation = useMutation({
    mutationFn: async (order: any) => {
      if (order.status === 'pending_admin_approval') {
        await api.post(`/api/v1/orders/${order.id}/approve`);
      }
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
    <>
    <div className="hidden md:block overflow-x-auto min-h-[150px]">
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
                  {(order.status === 'pending_admin_approval' || order.status === 'pending_broker_change_approval' || order.status === 'approved' || order.status === 'approved_waiting_for_mt5_id') && (
                    <button 
                      onClick={() => {
                        setSelectedOrder(order);
                        setInstallmentMode(false);
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
    
    {/* Mobile Card View */}
    <div className="md:hidden divide-y divide-neutral-800">
      {tableOrders.length === 0 ? (
        <div className="p-8 text-center text-neutral-500">No EA orders found.</div>
      ) : (
        tableOrders.map((order: any) => (
          <div key={order.id} className="p-3 space-y-2">
            <div className="flex justify-between items-start">
              <span className="font-medium text-white text-xs">#{order.id}</span>
              {getStatusBadge(order.status)}
            </div>
            
            <div className="grid grid-cols-2 gap-2 text-xs mt-1">
              <div>
                <span className="text-neutral-500 block text-[10px] mb-0.5">Product</span>
                <span className="text-neutral-300">{order.product}</span>
              </div>
              <div>
                <span className="text-neutral-500 block text-[10px] mb-0.5">Customer</span>
                <span className="text-neutral-300">{order.customer}</span>
              </div>
              <div>
                <span className="text-neutral-500 block text-[10px] mb-0.5">MT5 ID</span>
                <span className="text-white font-mono">{order.mt5_id || 'N/A'}</span>
              </div>
              <div>
                <span className="text-neutral-500 block text-[10px] mb-0.5">Date</span>
                <span className="text-neutral-300">{new Date(order.date || Date.now()).toLocaleDateString('en-GB')}</span>
              </div>
            </div>

            {(order.status === 'pending_admin_approval' || order.status === 'pending_broker_change_approval' || order.status === 'approved' || order.status === 'approved_waiting_for_mt5_id') && (
              <div className="flex justify-end gap-2 flex-wrap pt-3 border-t border-neutral-800/50">
                <button 
                  onClick={() => {
                    setSelectedOrder(order);
                    setInstallmentMode(false);
                    setApproveModalOpen(true);
                  }}
                  className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium text-emerald-400 bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/20 rounded-lg transition-colors"
                >
                  <ShieldCheck size={14} /> Process Approval
                </button>
              </div>
            )}
          </div>
        ))
      )}
    </div>
    </>
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

      {otherOrders.length > 0 && (
        <div className="bg-neutral-900 border border-neutral-800 rounded-xl overflow-hidden">
          <div className="px-6 py-4 border-b border-neutral-800 bg-neutral-900/50">
            <h2 className="text-sm font-semibold text-white">Completed / Other Orders</h2>
          </div>
          {renderTable(otherOrders)}
        </div>
      )}

      {approveModalOpen && selectedOrder && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-neutral-900 border border-neutral-800 rounded-xl w-full max-w-md shadow-2xl overflow-hidden flex flex-col max-h-[90dvh]">
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
            
            <div className="p-6 space-y-4 overflow-y-auto">
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
              ) : selectedOrder.is_broker_change ? (
                <div className="space-y-3">
                  <p className="text-sm text-neutral-300 text-center mb-4">Would you like to approve this broker change?</p>
                  
                  <button
                    disabled={approveBrokerChangeMutation.isPending}
                    onClick={() => approveBrokerChangeMutation.mutate(selectedOrder)}
                    className="w-full flex items-center justify-center p-3 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg font-medium transition-colors disabled:opacity-50"
                  >
                    {approveBrokerChangeMutation.isPending ? (
                      <Loader2 size={18} className="animate-spin" />
                    ) : (
                      <>
                        <ShieldCheck size={18} className="mr-2" />
                        Approve Broker Change
                      </>
                    )}
                  </button>

                  <button
                    disabled={rejectBrokerChangeMutation.isPending}
                    onClick={() => rejectBrokerChangeMutation.mutate(selectedOrder)}
                    className="w-full flex items-center justify-center p-3 bg-red-600/20 hover:bg-red-600/40 text-red-400 border border-red-500/30 rounded-lg font-medium transition-colors disabled:opacity-50"
                  >
                    {rejectBrokerChangeMutation.isPending ? (
                      <Loader2 size={18} className="animate-spin" />
                    ) : (
                      <>
                        Reject Request
                      </>
                    )}
                  </button>
                </div>
              ) : installmentMode ? (
                <div className="space-y-4 mt-2">
                  <div>
                    <label className="block text-xs font-medium text-neutral-400 mb-1">Total Amount (₹)</label>
                    <input 
                      type="number" 
                      value={totalAmount}
                      onChange={(e) => setTotalAmount(e.target.value)}
                      placeholder="e.g. 50000"
                      className="w-full bg-neutral-950 border border-neutral-800 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-emerald-500"
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <label className="block text-xs font-medium text-neutral-400 mb-1">Installment Amount (₹)</label>
                      <input 
                        type="number" 
                        value={installmentAmount}
                        onChange={(e) => { setInstallmentAmount(e.target.value); if(!firstPayment) setFirstPayment(e.target.value); }}
                        placeholder="e.g. 5000"
                        className="w-full bg-neutral-950 border border-neutral-800 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-emerald-500"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-neutral-400 mb-1">No. of Installments</label>
                      <input 
                        type="number" 
                        value={installmentCount}
                        onChange={(e) => setInstallmentCount(e.target.value)}
                        placeholder="e.g. 10"
                        className="w-full bg-neutral-950 border border-neutral-800 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-emerald-500"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-neutral-400 mb-1">First Payment Recv (₹)</label>
                      <input 
                        type="number" 
                        value={firstPayment}
                        onChange={(e) => setFirstPayment(e.target.value)}
                        placeholder="e.g. 5000"
                        className="w-full bg-neutral-950 border border-neutral-800 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-emerald-500"
                      />
                    </div>
                    <div>
                      <label className="block text-xs font-medium text-neutral-400 mb-1">License Days</label>
                      <input 
                        type="number" 
                        value={licenseDays}
                        onChange={(e) => setLicenseDays(e.target.value)}
                        placeholder="e.g. 30"
                        className="w-full bg-neutral-950 border border-neutral-800 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-emerald-500"
                      />
                    </div>
                  </div>
                  
                  <div className="flex gap-2 pt-2">
                    <button
                      onClick={() => setInstallmentMode(false)}
                      className="flex-1 py-2 text-neutral-400 bg-neutral-800/50 hover:bg-neutral-800 rounded-lg transition-colors"
                    >
                      Back
                    </button>
                    <button
                      disabled={createInstallmentMutation.isPending || !totalAmount || !installmentAmount || !installmentCount || !licenseDays}
                      onClick={() => createInstallmentMutation.mutate()}
                      className="flex-1 flex items-center justify-center py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded-lg font-medium transition-colors"
                    >
                      {createInstallmentMutation.isPending ? <Loader2 size={16} className="animate-spin" /> : "Save & Create"}
                    </button>
                  </div>
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
                      setInstallmentMode(true);
                      setTotalAmount('50000');
                      setInstallmentAmount('5000');
                      setInstallmentCount('10');
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
