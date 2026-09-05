'use client';

import { useState, FormEvent, useRef, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Server, Check, X, Loader2, MessageSquare, Send, XCircle } from 'lucide-react';
import api from '@/lib/api';
import { useToast } from '@/app/providers';

const getStatusColor = (status: string) => {
  switch (status?.toLowerCase()) {
    case 'pending': return 'bg-yellow-500/10 text-yellow-500 border-yellow-500/20';
    case 'contacted': return 'bg-blue-500/10 text-blue-400 border-blue-500/20';
    case 'paid': return 'bg-purple-500/10 text-purple-400 border-purple-500/20';
    case 'provisioned': return 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20';
    case 'rejected': return 'bg-red-500/10 text-red-400 border-red-500/20';
    default: return 'bg-neutral-800 text-neutral-400 border-neutral-700';
  }
};

const STATUS_LABELS: Record<string, string> = {
  pending: 'Pending',
  contacted: 'Contacted',
  paid: 'Paid',
  provisioned: 'Provisioned',
  rejected: 'Rejected',
};


const StatusDropdown = ({ order, onStatusChange }: { order: any, onStatusChange: (id: number, status: string) => void }) => {
  const [isOpen, setIsOpen] = useState(false);
  const statusColor = getStatusColor(order.status);
  const dropdownRef = useRef<HTMLDivElement>(null);
  
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const isLocked = order.status === 'provisioned' || order.status === 'rejected';

  return (
    <div className="relative" ref={dropdownRef}>
      <button 
        onClick={() => { if(!isLocked) setIsOpen(!isOpen); }}
        disabled={isLocked}
        className={`flex items-center justify-between w-32 border text-xs rounded-full px-3 py-1.5 font-medium focus:outline-none transition-colors ${statusColor} ${isLocked ? 'opacity-70 cursor-not-allowed' : 'hover:opacity-80 cursor-pointer'}`}
      >
        <span>{STATUS_LABELS[order.status] ?? order.status}</span>
        {!isLocked && (
          <svg className={`w-3 h-3 transition-transform ${isOpen ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7"></path></svg>
        )}
      </button>
      
      {isOpen && (
        <div className="absolute top-full left-0 mt-1 w-36 bg-neutral-900 border border-neutral-800 rounded-lg shadow-xl z-50 overflow-hidden">
          {['pending', 'contacted', 'paid', 'provisioned'].map(s => (
            <div 
              key={s} 
              onClick={() => { onStatusChange(order.id, s); setIsOpen(false); }} 
              className={`px-4 py-2 text-xs cursor-pointer transition-colors hover:bg-neutral-800 flex items-center ${order.status === s ? 'bg-neutral-800/50 text-white' : 'text-neutral-400'}`}
            >
              <span className={`mr-2 ${getStatusColor(s).split(' ')[1]}`}>●</span> 
              {STATUS_LABELS[s] ?? s}
            </div>
          ))}
          <div 
            onClick={() => { onStatusChange(order.id, 'rejected'); setIsOpen(false); }} 
            className="px-4 py-2 text-xs cursor-pointer transition-colors hover:bg-red-500/10 flex items-center text-red-400 border-t border-neutral-800"
          >
            <span className="mr-2">✕</span> Reject Order
          </div>
        </div>
      )}
    </div>
  );
};

export default function VpsOrdersPage() {
  const { toast } = useToast();
  const queryClient = useQueryClient();
  const [selectedOrder, setSelectedOrder] = useState<any>(null);
  const [hostname, setHostname] = useState('');
  const [ip, setIp] = useState('');
  const [username, setUsername] = useState('Administrator');
  const [password, setPassword] = useState('');
  const [purchasedDate, setPurchasedDate] = useState('');
  const [expiryDate, setExpiryDate] = useState('');
  
  // Message Modal state
  const [msgModalOpen, setMsgModalOpen] = useState(false);
  const [msgOrder, setMsgOrder] = useState<any>(null);
  const [messageText, setMessageText] = useState('');

  const { data: vpsOrders = [], isLoading, error } = useQuery({
    queryKey: ['admin-vps-orders'],
    refetchInterval: 15000,
    refetchIntervalInBackground: true,
    queryFn: async () => {
      const { data } = await api.get('/api/v1/admin/vps-orders');
      return data;
    }
  });

  const pendingStatuses = ['pending', 'contacted', 'paid'];
  const pendingOrders = Array.isArray(vpsOrders) ? vpsOrders.filter((o: any) => pendingStatuses.includes(o.status)) : [];
  const completedOrders = Array.isArray(vpsOrders) ? vpsOrders.filter((o: any) => !pendingStatuses.includes(o.status)) : [];

  const provisionMutation = useMutation({
    mutationFn: async (payload: any) => {
      const { data } = await api.post(`/api/v1/admin/vps-orders/${selectedOrder.id}/provision`, payload);
      return data;
    },
    onSuccess: (data: any) => {
      queryClient.invalidateQueries({ queryKey: ['admin-vps-orders'] });
      if (data?.warning) {
        toast(`VPS provisioned in DB ✅ — but Telegram notification failed: ${data.warning}`, "error");
      } else {
        toast("VPS provisioned and user notified via Telegram. ✅", "success");
      }
      closeModal();
    },
    onError: (error: any) => {
      toast(error.response?.data?.detail || "Failed to provision VPS", "error");
    }
  });

  const statusMutation = useMutation({
    mutationFn: async ({ id, status }: { id: number, status: string }) => {
      const { data } = await api.put(`/api/v1/admin/vps-orders/${id}/status`, { status });
      return data;
    },
    onMutate: async (newStatus) => {
      await queryClient.cancelQueries({ queryKey: ['admin-vps-orders'] });
      await queryClient.cancelQueries({ queryKey: ['admin-orders'] });
      const previousOrders = queryClient.getQueryData(['admin-vps-orders']);
      queryClient.setQueryData(['admin-vps-orders'], (old: any) => {
        if (!old) return old;
        return old.map((order: any) => 
          order.id === newStatus.id ? { ...order, status: newStatus.status } : order
        );
      });
      return { previousOrders };
    },
    onError: (err, newStatus, context: any) => {
      if (context?.previousOrders) {
        queryClient.setQueryData(['admin-vps-orders'], context.previousOrders);
      }
      toast("Failed to update status", "error");
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-vps-orders'] });
      queryClient.invalidateQueries({ queryKey: ['admin-orders'] });
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
      toast("Message sent to customer!", 'success');
    },
    onError: (err: any) => {
      toast("Failed to send message: " + (err.response?.data?.detail || err.message), 'error');
    }
  });

  const openModal = (order: any) => {
    setSelectedOrder(order);
    setHostname('');
    setIp('');
    setUsername('Administrator');
    setPassword('');
    const now = new Date();
    const localNowISO = new Date(now.getTime() - (now.getTimezoneOffset() * 60000)).toISOString().slice(0, 16);
    setPurchasedDate(localNowISO);
    if (order.duration) {
      const expiry = new Date(now);
      expiry.setMonth(expiry.getMonth() + order.duration);
      const localExpiryISO = new Date(expiry.getTime() - (expiry.getTimezoneOffset() * 60000)).toISOString().slice(0, 16);
      setExpiryDate(localExpiryISO);
    } else {
      setExpiryDate('');
    }
  };

  const closeModal = () => {
    setSelectedOrder(null);
    setHostname('');
    setIp('');
    setPassword('');
    setPurchasedDate('');
    setExpiryDate('');
  };

  const handleProvision = (e: FormEvent) => {
    e.preventDefault();
    provisionMutation.mutate({ 
      hostname, 
      ip, 
      username, 
      password, 
      purchased_date: purchasedDate ? new Date(purchasedDate).toISOString() : null, 
      expiry_date: expiryDate ? new Date(expiryDate).toISOString() : null 
    });
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

  if (error && (!vpsOrders || (Array.isArray(vpsOrders) && vpsOrders.length === 0) || (typeof vpsOrders === 'object' && Object.keys(vpsOrders).length === 0))) {
    return (
      <div className="bg-red-500/10 border border-red-500/20 text-red-400 p-4 rounded-lg">
        Failed to load VPS orders.
      </div>
    );
  }

  return (
    <div className="space-y-4 relative">
      <div>
        <h1 className="text-xl md:text-2xl font-bold text-white tracking-tight">VPS Provisioning</h1>
        <p className="text-sm text-neutral-400 mt-0.5">Manage and provision VPS servers for customers.</p>
      </div>

      <div>
        {/* Desktop Table */}
        
        <div className="hidden md:flex flex-col gap-6">
          <div className="bg-neutral-900 border border-neutral-800 rounded-xl overflow-hidden">
            <div className="px-6 py-4 border-b border-neutral-800 bg-neutral-900/50">
              <h3 className="font-semibold text-white">Pending Action</h3>
            </div>
            <div className=" overflow-x-auto ">
          <table className="min-w-full text-sm text-left">
            <thead className="text-xs text-neutral-400 bg-neutral-900/50 uppercase border-b border-neutral-800">
              <tr>
                <th className="px-6 py-4 whitespace-nowrap">Order ID</th>
                <th className="px-6 py-4">Customer</th>
                <th className="px-6 py-4">Plan</th>
                <th className="px-6 py-4">Terminals</th>
                <th className="px-6 py-4">Status</th>
                <th className="px-6 py-4">Expiry</th>
                <th className="px-6 py-4 text-right whitespace-nowrap">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-800">
              {pendingOrders.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-6 py-8 text-center text-neutral-500">
                    No pending action required.
                  </td>
                </tr>
              ) : (
                pendingOrders.map((order: any) => (
                  <tr key={order.id} className="hover:bg-neutral-800/30 transition-colors">
                    <td className="px-6 py-4 font-medium text-neutral-300 whitespace-nowrap">#{order.order_id || order.id}</td>
                    <td className="px-6 py-4 text-white">{order.customer || 'Guest'}</td>
                    <td className="px-6 py-4 text-neutral-400 whitespace-nowrap">
                      <span className="flex items-center gap-2">
                        {order.plan_name || 'Standard'}
                        {order.is_renewal && (
                          <span className="px-1.5 py-0.5 bg-blue-500/20 text-blue-400 border border-blue-500/30 rounded text-[10px] font-bold uppercase tracking-wider">
                            🔄 Renewal
                          </span>
                        )}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-neutral-400">{order.terminals_allowed || 2}</td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        {order.is_renewal ? (
                          <span className={`inline-flex items-center justify-center w-32 border text-xs rounded-full px-3 py-1.5 font-medium capitalize whitespace-nowrap ${
                            order.status === 'delivered' || order.status === 'provisioned' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' :
                            'bg-yellow-500/10 text-yellow-400 border-yellow-500/20'
                          }`}>
                            {(order.status || 'Unknown').replace(/_/g, ' ')}
                          </span>
                        ) : (
                          <StatusDropdown order={order} onStatusChange={(id, st) => statusMutation.mutate({ id, status: st })} />
                        )}
                        {order.screenshot_received && (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-bold bg-red-500/20 text-red-400 border border-red-500/30 animate-pulse whitespace-nowrap">
                            📸 SS Received
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-4 text-neutral-400 whitespace-nowrap">
                      {order.expiry_date ? new Date(order.expiry_date).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }) : '-'}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <button 
                          onClick={() => { setMsgOrder(order); setMsgModalOpen(true); }}
                          className="p-2 text-neutral-400 hover:text-white hover:bg-neutral-700 rounded transition-colors"
                          title="Send Message"
                        >
                          <MessageSquare size={16} />
                        </button>
                        {order.status !== 'provisioned' && order.status !== 'delivered' && order.status !== 'rejected' && (
                          order.is_renewal ? (
                            <>
                              <button 
                                onClick={() => {
                                  api.post(`/api/v1/orders/${order.order_id}/approve`).then(() => {
                                    toast("Renewal Approved!", "success");
                                    queryClient.invalidateQueries({ queryKey: ['admin-vps-orders'] });
                                  }).catch(() => toast("Failed to approve", "error"));
                                }}
                                className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded text-xs font-medium transition-colors"
                              >
                                Approve
                              </button>
                              <button 
                                onClick={() => {
                                  api.post(`/api/v1/orders/${order.order_id}/reject`).then(() => {
                                    toast("Renewal Rejected", "success");
                                    queryClient.invalidateQueries({ queryKey: ['admin-vps-orders'] });
                                  }).catch(() => toast("Failed to reject", "error"));
                                }}
                                className="px-3 py-1.5 bg-red-600/20 hover:bg-red-600/40 text-red-400 border border-red-500/30 rounded text-xs font-medium transition-colors"
                              >
                                Reject
                              </button>
                            </>
                          ) : (
                            <button 
                              onClick={() => openModal(order)}
                              className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded text-xs font-medium transition-colors"
                            >
                              Provision
                            </button>
                          )
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>


          </div>
          
          <div className="bg-neutral-900 border border-neutral-800 rounded-xl overflow-hidden">
            <div className="px-6 py-4 border-b border-neutral-800 bg-neutral-900/50">
              <h3 className="font-semibold text-white">Completed / Other Orders</h3>
            </div>
            <div className=" overflow-x-auto ">
          <table className="min-w-full text-sm text-left">
            <thead className="text-xs text-neutral-400 bg-neutral-900/50 uppercase border-b border-neutral-800">
              <tr>
                <th className="px-6 py-4 whitespace-nowrap">Order ID</th>
                <th className="px-6 py-4">Customer</th>
                <th className="px-6 py-4">Plan</th>
                <th className="px-6 py-4">Terminals</th>
                <th className="px-6 py-4">Status</th>
                <th className="px-6 py-4">Expiry</th>
                <th className="px-6 py-4 text-right whitespace-nowrap">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-800">
              {completedOrders.length === 0 ? (
                <tr>
                  <td colSpan={7} className="px-6 py-8 text-center text-neutral-500">
                    No completed orders.
                  </td>
                </tr>
              ) : (
                completedOrders.map((order: any) => (
                  <tr key={order.id} className="hover:bg-neutral-800/30 transition-colors">
                    <td className="px-6 py-4 font-medium text-neutral-300 whitespace-nowrap">#{order.order_id || order.id}</td>
                    <td className="px-6 py-4 text-white">{order.customer || 'Guest'}</td>
                    <td className="px-6 py-4 text-neutral-400 whitespace-nowrap">
                      <span className="flex items-center gap-2">
                        {order.plan_name || 'Standard'}
                        {order.is_renewal && (
                          <span className="px-1.5 py-0.5 bg-blue-500/20 text-blue-400 border border-blue-500/30 rounded text-[10px] font-bold uppercase tracking-wider">
                            🔄 Renewal
                          </span>
                        )}
                      </span>
                    </td>
                    <td className="px-6 py-4 text-neutral-400">{order.terminals_allowed || 2}</td>
                    <td className="px-6 py-4">
                      <div className="flex items-center gap-2">
                        {order.is_renewal ? (
                          <span className={`inline-flex items-center justify-center w-32 border text-xs rounded-full px-3 py-1.5 font-medium capitalize whitespace-nowrap ${
                            order.status === 'delivered' || order.status === 'provisioned' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' :
                            'bg-yellow-500/10 text-yellow-400 border-yellow-500/20'
                          }`}>
                            {(order.status || 'Unknown').replace(/_/g, ' ')}
                          </span>
                        ) : (
                          <StatusDropdown order={order} onStatusChange={(id, st) => statusMutation.mutate({ id, status: st })} />
                        )}
                        {order.screenshot_received && (
                          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-bold bg-red-500/20 text-red-400 border border-red-500/30 animate-pulse whitespace-nowrap">
                            📸 SS Received
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-6 py-4 text-neutral-400 whitespace-nowrap">
                      {order.expiry_date ? new Date(order.expiry_date).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }) : '-'}
                    </td>
                    <td className="px-6 py-4 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <button 
                          onClick={() => { setMsgOrder(order); setMsgModalOpen(true); }}
                          className="p-2 text-neutral-400 hover:text-white hover:bg-neutral-700 rounded transition-colors"
                          title="Send Message"
                        >
                          <MessageSquare size={16} />
                        </button>
                        {order.status !== 'provisioned' && order.status !== 'delivered' && order.status !== 'rejected' && (
                          order.is_renewal ? (
                            <>
                              <button 
                                onClick={() => {
                                  api.post(`/api/v1/orders/${order.order_id}/approve`).then(() => {
                                    toast("Renewal Approved!", "success");
                                    queryClient.invalidateQueries({ queryKey: ['admin-vps-orders'] });
                                  }).catch(() => toast("Failed to approve", "error"));
                                }}
                                className="px-3 py-1.5 bg-emerald-600 hover:bg-emerald-500 text-white rounded text-xs font-medium transition-colors"
                              >
                                Approve
                              </button>
                              <button 
                                onClick={() => {
                                  api.post(`/api/v1/orders/${order.order_id}/reject`).then(() => {
                                    toast("Renewal Rejected", "success");
                                    queryClient.invalidateQueries({ queryKey: ['admin-vps-orders'] });
                                  }).catch(() => toast("Failed to reject", "error"));
                                }}
                                className="px-3 py-1.5 bg-red-600/20 hover:bg-red-600/40 text-red-400 border border-red-500/30 rounded text-xs font-medium transition-colors"
                              >
                                Reject
                              </button>
                            </>
                          ) : (
                            <button 
                              onClick={() => openModal(order)}
                              className="px-3 py-1.5 bg-blue-600 hover:bg-blue-500 text-white rounded text-xs font-medium transition-colors"
                            >
                              Provision
                            </button>
                          )
                        )}
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>


          </div>
        </div>
        {/* Mobile Card Layout */}
        
        <div className="md:hidden flex flex-col gap-6">
          <div className="bg-neutral-900 border border-neutral-800 rounded-xl overflow-hidden">
            <div className="px-4 py-3 border-b border-neutral-800 bg-neutral-900/50">
              <h3 className="font-semibold text-white text-sm">Pending Action</h3>
            </div>
            <div className="flex flex-col divide-y divide-neutral-800">
          {pendingOrders.length === 0 ? (
            <div className="p-8 text-center text-neutral-500">No pending action required.</div>
          ) : (
            pendingOrders.map((order: any) => (
              <div key={order.id} className="p-3 space-y-2">
                <div className="flex justify-between items-start">
                  <span className="font-medium text-white text-xs">#{order.order_id || order.id}</span>
                  <div className="flex flex-col items-end gap-1">
                    {order.is_renewal ? (
                      <span className={`inline-flex items-center justify-center w-32 border text-xs rounded-full px-3 py-1.5 font-medium capitalize whitespace-nowrap ${
                        order.status === 'delivered' || order.status === 'provisioned' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' :
                        order.status === 'rejected' ? 'bg-red-500/10 text-red-400 border-red-500/20' :
                        'bg-yellow-500/10 text-yellow-400 border-yellow-500/20'
                      }`}>
                        {STATUS_LABELS[order.status] || (order.status || 'Unknown').replace(/_/g, ' ')}
                      </span>
                    ) : (
                      <StatusDropdown order={order} onStatusChange={(id, st) => statusMutation.mutate({ id, status: st })} />
                    )}
                    {order.screenshot_received && (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-red-500/20 text-red-400 border border-red-500/30 animate-pulse whitespace-nowrap">
                        📸 SS
                      </span>
                    )}
                  </div>
                </div>
                
                <div className="grid grid-cols-2 gap-x-2 gap-y-1.5 text-xs mt-1">
                  <div>
                    <span className="text-neutral-500 block text-[10px]">Customer</span>
                    <span className="text-neutral-300">{order.customer_name || order.customer || 'Guest'}</span>
                  </div>
                  <div>
                    <span className="text-neutral-500 block text-[10px]">Plan</span>
                    <span className="text-white font-medium flex items-center gap-1 flex-wrap">
                      {order.plan_name}
                      {order.is_renewal && (
                        <span className="px-1 py-0.5 bg-blue-500/20 text-blue-400 border border-blue-500/30 rounded text-[9px] font-bold uppercase">🔄 RENEWAL</span>
                      )}
                    </span>
                  </div>
                  <div>
                    <span className="text-neutral-500 block text-[10px]">Terminals</span>
                    <span className="text-neutral-300">{order.terminals_allowed || 2}</span>
                  </div>
                  <div>
                    <span className="text-neutral-500 block text-[10px]">Expiry Date</span>
                    <span className="text-neutral-300">
                      {order.expiry_date ? new Date(order.expiry_date).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }) : '-'}
                    </span>
                  </div>
                </div>

                <div className="flex justify-end gap-2 flex-wrap pt-2 border-t border-neutral-800/50">
                  <button 
                    onClick={() => { setMsgOrder(order); setMsgModalOpen(true); }}
                    className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs text-blue-400 bg-blue-500/10 hover:bg-blue-500/20 border border-blue-500/20 rounded-lg transition-colors">
                    <MessageSquare size={13} /> Message
                  </button>
                  {order.status !== 'provisioned' && order.status !== 'delivered' && order.status !== 'rejected' && (
                    order.is_renewal ? (
                      <>
                        <button 
                          onClick={() => {
                            api.post(`/api/v1/orders/${order.order_id}/approve`).then(() => {
                              toast("Renewal Approved!", "success");
                              queryClient.invalidateQueries({ queryKey: ['admin-vps-orders'] });
                            }).catch(() => toast("Failed to approve", "error"));
                          }}
                          className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs text-emerald-400 bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/20 rounded-lg transition-colors">
                          <Check size={13} /> Approve
                        </button>
                        <button 
                          onClick={() => {
                            api.post(`/api/v1/orders/${order.order_id}/reject`).then(() => {
                              toast("Renewal Rejected", "success");
                              queryClient.invalidateQueries({ queryKey: ['admin-vps-orders'] });
                            }).catch(() => toast("Failed to reject", "error"));
                          }}
                          className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs text-red-400 bg-red-500/10 hover:bg-red-500/20 border border-red-500/20 rounded-lg transition-colors">
                          <XCircle size={13} /> Reject
                        </button>
                      </>
                    ) : (
                      <button 
                        onClick={() => openModal(order)}
                        className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs text-emerald-400 bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/20 rounded-lg transition-colors">
                        <Check size={13} /> Provision
                      </button>
                    )
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      
          </div>
          
          <div className="bg-neutral-900 border border-neutral-800 rounded-xl overflow-hidden">
            <div className="px-4 py-3 border-b border-neutral-800 bg-neutral-900/50">
              <h3 className="font-semibold text-white text-sm">Completed / Other Orders</h3>
            </div>
            <div className="flex flex-col divide-y divide-neutral-800">
          {completedOrders.length === 0 ? (
            <div className="p-8 text-center text-neutral-500">No completed orders.</div>
          ) : (
            completedOrders.map((order: any) => (
              <div key={order.id} className="p-3 space-y-2">
                <div className="flex justify-between items-start">
                  <span className="font-medium text-white text-xs">#{order.order_id || order.id}</span>
                  <div className="flex flex-col items-end gap-1">
                    {order.is_renewal ? (
                      <span className={`inline-flex items-center justify-center w-32 border text-xs rounded-full px-3 py-1.5 font-medium capitalize whitespace-nowrap ${
                        order.status === 'delivered' || order.status === 'provisioned' ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20' :
                        order.status === 'rejected' ? 'bg-red-500/10 text-red-400 border-red-500/20' :
                        'bg-yellow-500/10 text-yellow-400 border-yellow-500/20'
                      }`}>
                        {STATUS_LABELS[order.status] || (order.status || 'Unknown').replace(/_/g, ' ')}
                      </span>
                    ) : (
                      <StatusDropdown order={order} onStatusChange={(id, st) => statusMutation.mutate({ id, status: st })} />
                    )}
                    {order.screenshot_received && (
                      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold bg-red-500/20 text-red-400 border border-red-500/30 animate-pulse whitespace-nowrap">
                        📸 SS
                      </span>
                    )}
                  </div>
                </div>
                
                <div className="grid grid-cols-2 gap-x-2 gap-y-1.5 text-xs mt-1">
                  <div>
                    <span className="text-neutral-500 block text-[10px]">Customer</span>
                    <span className="text-neutral-300">{order.customer_name || order.customer || 'Guest'}</span>
                  </div>
                  <div>
                    <span className="text-neutral-500 block text-[10px]">Plan</span>
                    <span className="text-white font-medium flex items-center gap-1 flex-wrap">
                      {order.plan_name}
                      {order.is_renewal && (
                        <span className="px-1 py-0.5 bg-blue-500/20 text-blue-400 border border-blue-500/30 rounded text-[9px] font-bold uppercase">🔄 RENEWAL</span>
                      )}
                    </span>
                  </div>
                  <div>
                    <span className="text-neutral-500 block text-[10px]">Terminals</span>
                    <span className="text-neutral-300">{order.terminals_allowed || 2}</span>
                  </div>
                  <div>
                    <span className="text-neutral-500 block text-[10px]">Expiry Date</span>
                    <span className="text-neutral-300">
                      {order.expiry_date ? new Date(order.expiry_date).toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric' }) : '-'}
                    </span>
                  </div>
                </div>

                <div className="flex justify-end gap-2 flex-wrap pt-2 border-t border-neutral-800/50">
                  <button 
                    onClick={() => { setMsgOrder(order); setMsgModalOpen(true); }}
                    className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs text-blue-400 bg-blue-500/10 hover:bg-blue-500/20 border border-blue-500/20 rounded-lg transition-colors">
                    <MessageSquare size={13} /> Message
                  </button>
                  {order.status !== 'provisioned' && order.status !== 'delivered' && order.status !== 'rejected' && (
                    order.is_renewal ? (
                      <>
                        <button 
                          onClick={() => {
                            api.post(`/api/v1/orders/${order.order_id}/approve`).then(() => {
                              toast("Renewal Approved!", "success");
                              queryClient.invalidateQueries({ queryKey: ['admin-vps-orders'] });
                            }).catch(() => toast("Failed to approve", "error"));
                          }}
                          className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs text-emerald-400 bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/20 rounded-lg transition-colors">
                          <Check size={13} /> Approve
                        </button>
                        <button 
                          onClick={() => {
                            api.post(`/api/v1/orders/${order.order_id}/reject`).then(() => {
                              toast("Renewal Rejected", "success");
                              queryClient.invalidateQueries({ queryKey: ['admin-vps-orders'] });
                            }).catch(() => toast("Failed to reject", "error"));
                          }}
                          className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs text-red-400 bg-red-500/10 hover:bg-red-500/20 border border-red-500/20 rounded-lg transition-colors">
                          <XCircle size={13} /> Reject
                        </button>
                      </>
                    ) : (
                      <button 
                        onClick={() => openModal(order)}
                        className="flex items-center gap-1.5 px-2.5 py-1.5 text-xs text-emerald-400 bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/20 rounded-lg transition-colors">
                        <Check size={13} /> Provision
                      </button>
                    )
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      
          </div>
        </div>

      {/* Provisioning Modal */}
      {selectedOrder && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-neutral-900 border border-neutral-800 rounded-xl w-full max-w-md shadow-2xl overflow-hidden flex flex-col max-h-[90dvh]">
            <div className="px-6 py-4 border-b border-neutral-800 flex items-center justify-between">
              <h3 className="text-lg font-bold text-white flex items-center">
                <Server size={18} className="mr-2 text-blue-400" />
                Provision VPS #{selectedOrder.id}
              </h3>
              <button onClick={closeModal} className="text-neutral-500 hover:text-white transition-colors">
                <X size={20} />
              </button>
            </div>
            
            <form onSubmit={handleProvision} className="p-6 space-y-4 overflow-y-auto">
              <div className="bg-neutral-950 p-3 rounded-lg border border-neutral-800 text-xs flex justify-between items-center mb-4">
                <span className="text-neutral-400">Product Plan:</span>
                <span className="text-white font-medium">{selectedOrder?.plan_name}</span>
              </div>
              
              <div>
                <label className="block text-xs font-medium text-neutral-400 mb-1">Hostname / Server Name</label>
                <input type="text" value={hostname} onChange={(e) => setHostname(e.target.value)}
                  placeholder="e.g. VPS-Node-01"
                  className="w-full bg-neutral-950 border border-neutral-800 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500" />
              </div>
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-xs font-medium text-neutral-400 mb-1">Main IP Address</label>
                  <input type="text" required value={ip} onChange={(e) => setIp(e.target.value)}
                    placeholder="e.g. 192.168.1.100"
                    className="w-full bg-neutral-950 border border-neutral-800 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-neutral-400 mb-1">Username</label>
                  <input type="text" required value={username} onChange={(e) => setUsername(e.target.value)}
                    className="w-full bg-neutral-950 border border-neutral-800 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500" />
                </div>
              </div>
              <div>
                <label className="block text-xs font-medium text-neutral-400 mb-1">Root Password</label>
                <input type="password" required value={password} onChange={(e) => setPassword(e.target.value)}
                  className="w-full bg-neutral-950 border border-neutral-800 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500" />
              </div>

              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="block text-xs font-medium text-neutral-400 mb-1">Purchased Date</label>
                  <input type="datetime-local" required value={purchasedDate} onChange={(e) => setPurchasedDate(e.target.value)}
                    className="w-full bg-neutral-950 border border-neutral-800 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-neutral-400 mb-1">Expiry Date & Time</label>
                  <input type="datetime-local" required value={expiryDate} onChange={(e) => setExpiryDate(e.target.value)}
                    className="w-full bg-neutral-950 border border-neutral-800 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500" />
                </div>
              </div>

              <div className="pt-4 flex justify-end space-x-3">
                <button type="button" onClick={closeModal} className="px-4 py-2 text-neutral-400 hover:text-white transition-colors">Cancel</button>
                <button type="submit" disabled={provisionMutation.isPending}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded-lg font-medium flex items-center transition-colors">
                  {provisionMutation.isPending ? (
                    <><Loader2 size={16} className="animate-spin mr-2" />Provisioning...</>
                  ) : (
                    <><Check size={16} className="mr-2" />Complete Provisioning</>
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
          <div className="bg-neutral-900 border border-neutral-800 rounded-xl w-full max-w-md shadow-2xl overflow-hidden flex flex-col max-h-[90dvh]">
            <div className="px-6 py-4 border-b border-neutral-800 flex items-center justify-between">
              <h3 className="text-lg font-bold text-white flex items-center">
                <MessageSquare size={18} className="mr-2 text-blue-400" />
                Message Customer
              </h3>
              <button onClick={() => setMsgModalOpen(false)} className="text-neutral-500 hover:text-white transition-colors">
                <X size={20} />
              </button>
            </div>
            
            <form onSubmit={handleSendMessage} className="p-6 space-y-4 overflow-y-auto">
              <div>
                <label className="block text-xs font-medium text-neutral-400 mb-1">Direct Message to {msgOrder.customer}</label>
                <textarea required rows={4} value={messageText} onChange={(e) => setMessageText(e.target.value)}
                  placeholder="Type your message to the customer here..."
                  className="w-full bg-neutral-950 border border-neutral-800 rounded-lg px-4 py-2 text-white focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500" />
              </div>
              <div className="pt-4 flex justify-end space-x-3">
                <button type="button" onClick={() => setMsgModalOpen(false)} className="px-4 py-2 text-neutral-400 hover:text-white transition-colors">Cancel</button>
                <button type="submit" disabled={messageMutation.isPending}
                  className="px-4 py-2 bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white rounded-lg font-medium flex items-center transition-colors">
                  {messageMutation.isPending ? <Loader2 size={16} className="animate-spin" /> : <><Send size={16} className="mr-2" />Send Message</>}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

    </div>
  );
}
