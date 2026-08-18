'use client';

import { useQuery } from '@tanstack/react-query';
import { Eye, Loader2, CheckCircle, Ban, History } from 'lucide-react';
import api from '@/lib/api';
import ConfirmModal from '@/components/ui/ConfirmModal';
import { useState } from 'react';

export default function InstallmentsPage() {
  const [payModalOpen, setPayModalOpen] = useState(false);
  const [disableModalOpen, setDisableModalOpen] = useState(false);
  const [selectedOrder, setSelectedOrder] = useState<any>(null);
  const [payAmount, setPayAmount] = useState<number>(0);
  const [processing, setProcessing] = useState(false);

  const { data: installments = [], isLoading, error, refetch } = useQuery({
    refetchInterval: 30000,
    queryKey: ['admin-installments'],
    queryFn: async () => {
      const { data } = await api.get('/api/v1/installments/admin/all');
      return data;
    }
  });

  const handlePayClick = (order: any) => {
    setSelectedOrder(order);
    setPayAmount(order.installment_amount);
    setPayModalOpen(true);
  };

  const handleDisableClick = (order: any) => {
    setSelectedOrder(order);
    setDisableModalOpen(true);
  };

  const handleRecordPayment = async () => {
    if (!selectedOrder) return;
    setProcessing(true);
    try {
      await api.post('/api/v1/installments/pay', {
        order_id: selectedOrder.order_id,
        amount: payAmount
      });
      setPayModalOpen(false);
      setSelectedOrder(null);
      refetch();
    } catch(e: any) {
      alert('Failed to record payment: ' + (e.response?.data?.detail || e.message));
    }
    setProcessing(false);
  };

  const handleDisableArrangement = async () => {
    if (!selectedOrder) return;
    setProcessing(true);
    try {
      await api.post(`/api/v1/installments/admin/disable/${selectedOrder.order_id}`);
      setDisableModalOpen(false);
      setSelectedOrder(null);
      refetch();
    } catch(e: any) {
      alert('Failed to disable arrangement: ' + (e.response?.data?.detail || e.message));
    }
    setProcessing(false);
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
        Failed to load installment arrangements.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Installments</h1>
          <p className="text-neutral-400 mt-1">Manage recurring EA license payments.</p>
        </div>
      </div>

      <div className="bg-neutral-900 border border-neutral-800 rounded-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead className="text-xs text-neutral-400 bg-neutral-900/50 uppercase border-b border-neutral-800">
              <tr>
                <th className="px-6 py-4">Order ID</th>
                <th className="px-6 py-4">MT5 ID</th>
                <th className="px-6 py-4">Status</th>
                <th className="px-6 py-4">Paid / Total</th>
                <th className="px-6 py-4">Remaining</th>
                <th className="px-6 py-4">Next Due</th>
                <th className="px-6 py-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-800">
              {installments.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-6 py-8 text-center text-neutral-500">
                    No installment plans found.
                  </td>
                </tr>
              ) : (
                installments.map((inst: any) => (
                  <tr key={inst.order_id} className="hover:bg-neutral-800/30 transition-colors">
                    <td className="px-6 py-4 font-medium text-neutral-300">#{inst.order_id}</td>
                    <td className="px-6 py-4 text-white">{inst.mt5_id || 'N/A'}</td>
                    <td className="px-6 py-4">
                      {inst.installment_status === 'active' && <span className="px-2 py-1 bg-blue-500/10 text-blue-400 rounded text-xs font-medium border border-blue-500/20">Active</span>}
                      {inst.installment_status === 'completed' && <span className="px-2 py-1 bg-emerald-500/10 text-emerald-400 rounded text-xs font-medium border border-emerald-500/20">Completed</span>}
                      {inst.installment_status === 'failed' && <span className="px-2 py-1 bg-red-500/10 text-red-400 rounded text-xs font-medium border border-red-500/20">Disabled</span>}
                    </td>
                    <td className="px-6 py-4 text-neutral-300">₹{inst.amount_paid} / ₹{inst.total_amount} ({inst.installments_paid}/{inst.installment_count})</td>
                    <td className="px-6 py-4 text-neutral-300">₹{inst.amount_remaining}</td>
                    <td className="px-6 py-4 text-neutral-400">
                      {inst.installment_status === 'completed' ? '-' : (inst.next_due_date ? new Date(inst.next_due_date).toLocaleString() : 'N/A')}
                    </td>
                    <td className="px-6 py-4 text-right flex items-center justify-end gap-1">
                      {inst.installment_status === 'active' && (
                        <>
                          <button 
                            onClick={() => handlePayClick(inst)}
                            className="p-2 text-neutral-400 hover:text-emerald-400 hover:bg-emerald-500/10 rounded transition-colors" title="Record Payment">
                            <CheckCircle size={16} />
                          </button>
                          <button 
                            onClick={() => handleDisableClick(inst)}
                            className="p-2 text-neutral-400 hover:text-red-500 hover:bg-red-500/10 rounded transition-colors" title="Disable Arrangement">
                            <Ban size={16} />
                          </button>
                        </>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    
      <ConfirmModal
        isOpen={payModalOpen}
        title="Record Payment"
        message={`Are you sure you want to record a payment of ₹${payAmount} for Order #${selectedOrder?.order_id}? This will automatically extend their license and push back the due date.`}
        confirmText={processing ? "Processing..." : "Record Payment"}
        cancelText="Cancel"
        isDestructive={false}
        onConfirm={handleRecordPayment}
        onCancel={() => {
          setPayModalOpen(false);
          setSelectedOrder(null);
        }}
      />

      <ConfirmModal
        isOpen={disableModalOpen}
        title="Disable Arrangement"
        message={`Are you sure you want to disable the arrangement for Order #${selectedOrder?.order_id}? This will revoke their EA license and stop tracking payments.`}
        confirmText={processing ? "Processing..." : "Disable"}
        cancelText="Cancel"
        isDestructive={true}
        onConfirm={handleDisableArrangement}
        onCancel={() => {
          setDisableModalOpen(false);
          setSelectedOrder(null);
        }}
      />
    </div>
  );
}
