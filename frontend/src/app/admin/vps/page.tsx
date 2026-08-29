'use client';

import { useState, FormEvent } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Server, Check, X, Loader2, MessageSquare, Send } from 'lucide-react';
import api from '@/lib/api';

export default function VpsOrdersPage() {
  const queryClient = useQueryClient();
  const [selectedOrder, setSelectedOrder] = useState<any>(null);
  const [ip, setIp] = useState('');
  const [username, setUsername] = useState('Administrator');
  const [password, setPassword] = useState('');
  
  // Message Modal state
  const [msgModalOpen, setMsgModalOpen] = useState(false);
  const [msgOrder, setMsgOrder] = useState<any>(null);
  const [messageText, setMessageText] = useState('');

  const { data: vpsOrders = [], isLoading, error } = useQuery({
    queryKey: ['admin-vps-orders'],
    queryFn: async () => {
      const { data } = await api.get('/api/v1/admin/vps-orders');
      return data;
    }
  });

  const provisionMutation = useMutation({
    mutationFn: async (payload: any) => {
      const { data } = await api.post(`/api/v1/admin/vps-orders/${selectedOrder.id}/provision`, payload);
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-vps-orders'] });
      closeModal();
    }
  });

  const statusMutation = useMutation({
    mutationFn: async ({ id, status }: { id: number, status: string }) => {
      const { data } = await api.put(`/api/v1/admin/vps-orders/${id}/status`, { status });
      return data;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-vps-orders'] });
    }
  });

  const messageMutation = useMutation({
    mutationFn: async ({ id, message }: { id: number, message: string }) => {
      const { data } = await api.post(`/api/v1/admin/vps-orders/${id}/message`, { message });
      return data;
    },
    onSuccess: () => {
      setMsgModalOpen(false);
      setMsgOrder(null);
      setMessageText('');
      alert("Message sent to customer!");
    },
    onError: (err: any) => {
      alert("Failed to send message: " + (err.response?.data?.detail || err.message));
    }
  });

  const openModal = (order: any) => {
    setSelectedOrder(order);
    setIp('');
    setUsername('Administrator');
    setPassword('');
  };

  const closeModal = () => {
    setSelectedOrder(null);
  };

  const handleProvision = (e: FormEvent) => {
    e.preventDefault();
    provisionMutation.mutate({ ip, username, password });
  };

  const handleSendMessage = (e: FormEvent) => {
    e.preventDefault();
    if (!msgOrder || !messageText.trim()) return;
    messageMutation.mutate({ id: msgOrder.id, message: messageText });
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
        Failed to load VPS orders.
      </div>
    );
  }

  return (
    <div className="space-y-6 relative">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">VPS Provisioning</h1>
          <p className="text-neutral-400 mt-1">Manage and provision VPS servers for customers.</p>
        </div>
      </div>

      <div className="bg-neutral-900 border border-neutral-800 rounded-xl overflow-hidden">
        <div className="overflow-x-auto [&::-webkit-scrollbar]:hidden [-ms-overflow-style:none] [scrollbar-width:none]">
          <table className="min-w-full text-sm text-left">
            <thead className="text-xs text-neutral-400 bg-neutral-900/50 uppercase border-b border-neutral-800">
              <tr>
                <th className="px-6 py-4 whitespace-nowrap">Order ID</th>
                <th className="px-6 py-4 hidden md:table-cell">Customer</th>
                <th className="px-6 py-4 hidden md:table-cell">Plan</th>
                <th className="px-6 py-4 hidden md:table-cell">Terminals</th>
                <th className="px-6 py-4">Status</th>
                <th className="px-6 py-4 text-right whitespace-nowrap">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-800">
              {vpsOrders.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-6 py-8 text-center text-neutral-500">
                    No VPS orders found.
                  </td>
                </tr>
              ) : (
                vpsOrders.map((order: any) => (
                  <tr key={order.id} className="hover:bg-neutral-800/30 transition-colors">
                    <td className="px-6 py-4 font-medium text-neutral-300 whitespace-nowrap">#{order.order_id || order.id}</td>
                    <td className="px-6 py-4 text-white hidden md:table-cell">{order.customer || 'Guest'}</td>
                    <td className="px-6 py-4 text-neutral-400 hidden md:table-cell whitespace-nowrap">{order.plan_name || 'Standard'}</td>
                    <td className="px-6 py-4 text-neutral-400 hidden md:table-cell">{order.terminals_allowed || 2}</td>
                    <td className="px-6 py-4">
                      <select
                        value={order.status}
                        onChange={(e) => statusMutation.mutate({ id: order.id, status: e.target.value })}
                        disabled={order.status === 'provisioned'}
                        className="bg-neutral-950 border border-neutral-800 text-xs rounded px-2 py-1 focus:outline-none focus:border-blue-500"
                      >
                        <option value="pending">Pending</option>
                        <option value="contacted">Contacted</option>
                        <option value="paid">Paid</option>
                        <option value="provisioned">Provisioned</option>
                      </select>
                    </td>
                    <td className="px-6 py-4 text-right space-x-2">
                      <button 
                        onClick={() => { setMsgOrder(order); setMsgModalOpen(true); }}
                        className="p-2 text-neutral-400 hover:text-white hover:bg-neutral-700 rounded transition-colors"
                        title="Send Message"
                      >
                        <MessageSquare size={16} />
                      </button>
                      {order.status !== 'provisioned' && (
                        <button 
                          onClick={() => openModal(order)}
                          className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded text-xs font-medium transition-colors"
                        >
                          Provision
                        </button>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Provisioning Modal */}
      {selectedOrder && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-neutral-900 border border-neutral-800 rounded-xl w-full max-w-md shadow-2xl overflow-hidden">
            <div className="px-6 py-4 border-b border-neutral-800 flex items-center justify-between">
              <h3 className="text-lg font-bold text-white flex items-center">
                <Server size={18} className="mr-2 text-blue-400" />
                Provision VPS #{selectedOrder.id}
              </h3>
              <button 
                onClick={closeModal}
                className="text-neutral-500 hover:text-white transition-colors"
              >
                <X size={20} />
              </button>
            </div>
            
            <form onSubmit={handleProvision} className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-neutral-400 mb-1">Server IP Address</label>
                <input 
                  type="text" 
                  required
                  value={ip}
                  onChange={(e) => setIp(e.target.value)}
                  placeholder="e.g. 192.168.1.100"
                  className="w-full bg-neutral-950 border border-neutral-800 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-neutral-400 mb-1">Username</label>
                <input 
                  type="text" 
                  required
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  className="w-full bg-neutral-950 border border-neutral-800 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-neutral-400 mb-1">Password</label>
                <input 
                  type="password" 
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full bg-neutral-950 border border-neutral-800 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                />
              </div>
              
              <div className="pt-4 flex justify-end space-x-3">
                <button 
                  type="button"
                  onClick={closeModal}
                  className="px-4 py-2 text-neutral-400 hover:text-white transition-colors"
                >
                  Cancel
                </button>
                <button 
                  type="submit"
                  disabled={provisionMutation.isPending}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded-lg font-medium flex items-center transition-colors"
                >
                  {provisionMutation.isPending ? (
                    <>
                      <Loader2 size={16} className="animate-spin mr-2" />
                      Provisioning...
                    </>
                  ) : (
                    <>
                      <Check size={16} className="mr-2" />
                      Complete Provisioning
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* Send Message Modal */}
      {msgModalOpen && msgOrder && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-neutral-900 border border-neutral-800 rounded-xl w-full max-w-md shadow-2xl overflow-hidden">
            <div className="px-6 py-4 border-b border-neutral-800 flex items-center justify-between">
              <h3 className="text-lg font-bold text-white flex items-center">
                <MessageSquare size={18} className="mr-2 text-blue-400" />
                Message Customer
              </h3>
              <button 
                onClick={() => setMsgModalOpen(false)}
                className="text-neutral-500 hover:text-white transition-colors"
              >
                <X size={20} />
              </button>
            </div>
            
            <form onSubmit={handleSendMessage} className="p-6 space-y-4">
              <div>
                <label className="block text-sm font-medium text-neutral-400 mb-1">Direct Message to {msgOrder.customer}</label>
                <textarea 
                  required
                  rows={4}
                  value={messageText}
                  onChange={(e) => setMessageText(e.target.value)}
                  placeholder="Type your message to the customer here..."
                  className="w-full bg-neutral-950 border border-neutral-800 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500"
                />
              </div>
              
              <div className="pt-4 flex justify-end space-x-3">
                <button 
                  type="button"
                  onClick={() => setMsgModalOpen(false)}
                  className="px-4 py-2 text-neutral-400 hover:text-white transition-colors"
                >
                  Cancel
                </button>
                <button 
                  type="submit"
                  disabled={messageMutation.isPending}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded-lg font-medium flex items-center transition-colors"
                >
                  {messageMutation.isPending ? (
                    <Loader2 size={16} className="animate-spin" />
                  ) : (
                    <>
                      <Send size={16} className="mr-2" />
                      Send Message
                    </>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
}
