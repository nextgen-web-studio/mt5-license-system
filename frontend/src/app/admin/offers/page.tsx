'use client';

import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useState } from 'react';
import { Loader2, Plus, Trash2, ToggleLeft, ToggleRight, Tag, ArrowRight } from 'lucide-react';
import api from '@/lib/api';
import { useToast } from '@/app/providers';

const formatDate = (d: string) => new Date(d).toLocaleString('en-IN', { timeZone: 'Asia/Kolkata', day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });
const isActive = (o: any) => o.active && new Date(o.starts_at) <= new Date() && new Date(o.expires_at) >= new Date();

export default function OffersPage() {
  const { toast } = useToast();
  const queryClient = useQueryClient();

  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({
    product_id: '',
    offer_label: '🔥 Flash Sale',
    offer_price: '',
    starts_at: new Date().toISOString().slice(0, 16),
    expires_at: '',
    active: true,
  });

  const { data: products = [] } = useQuery({
    queryKey: ['all-products'],
    queryFn: async () => { const { data } = await api.get('/api/v1/products'); return data; },
  });

  const { data: offers = [], isLoading } = useQuery({
    queryKey: ['admin-offers'],
    queryFn: async () => { const { data } = await api.get('/api/v1/offers'); return data; },
    refetchInterval: 2000,
  });

  const createMutation = useMutation({
    mutationFn: async () => {
      const payload = {
        ...form,
        product_id: parseInt(form.product_id),
        offer_price: parseFloat(form.offer_price),
        starts_at: new Date(form.starts_at).toISOString(),
        expires_at: new Date(form.expires_at).toISOString(),
      };
      const { data } = await api.post('/api/v1/offers', payload);
      return data;
    },
    onSuccess: () => {
      toast('Flash Sale Created', 'success');
      setShowForm(false);
      setForm({ product_id: '', offer_label: '🔥 Flash Sale', offer_price: '', starts_at: new Date().toISOString().slice(0, 16), expires_at: '', active: true });
      queryClient.invalidateQueries({ queryKey: ['admin-offers'] });
    },
    onError: (err: any) => toast('Error: ' + (err.response?.data?.detail || err.message), 'error'),
  });

  const toggleMutation = useMutation({
    mutationFn: async ({ id, active }: { id: number; active: boolean }) => {
      const { data } = await api.put(`/api/v1/offers/${id}`, { active });
      return data;
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin-offers'] }),
    onError: (err: any) => toast('Error: ' + (err.response?.data?.detail || err.message), 'error'),
  });

  const deleteMutation = useMutation({
    mutationFn: async (id: number) => { await api.delete(`/api/v1/offers/${id}`); },
    onSuccess: () => {
      toast('Offer deleted', 'delete');
      queryClient.invalidateQueries({ queryKey: ['admin-offers'] });
    },
    onError: (err: any) => toast('Error: ' + (err.response?.data?.detail || err.message), 'error'),
  });

  const selectedProduct = products.find((p: any) => p.id === parseInt(form.product_id));

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center gap-2"><Tag size={24} className="text-orange-400" /> Flash Sale Offers</h1>
          <p className="text-neutral-400 text-sm mt-1">Create limited-time discounts on EA or VPS products. Offers appear automatically in the Telegram bot.</p>
        </div>
        <button onClick={() => setShowForm(!showForm)} className="flex items-center justify-center gap-2 px-4 py-2 bg-orange-500 hover:bg-orange-400 text-white rounded-lg font-medium transition-colors text-sm w-full sm:w-auto shrink-0">
          <Plus size={16} /> New Offer
        </button>
      </div>

      {/* Create Form */}
      {showForm && (
        <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-5 space-y-4">
          <h2 className="text-white font-semibold text-lg">Create New Flash Sale</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="text-neutral-400 text-xs uppercase tracking-wide block mb-1">Product</label>
              <select value={form.product_id} onChange={e => setForm(f => ({ ...f, product_id: e.target.value }))}
                className="w-full bg-neutral-800 border border-neutral-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-orange-500">
                <option value="">-- Select Product --</option>
                {products.map((p: any) => (
                  <option key={p.id} value={p.id}>{p.type} — {p.name} (Normal: {p.type === 'EA' ? `$${p.price}` : `₹${p.price.toLocaleString('en-IN')}`})</option>
                ))}
              </select>
            </div>
            <div>
              <label className="text-neutral-400 text-xs uppercase tracking-wide block mb-1">Offer Label</label>
              <input value={form.offer_label} onChange={e => setForm(f => ({ ...f, offer_label: e.target.value }))}
                className="w-full bg-neutral-800 border border-neutral-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-orange-500"
                placeholder="e.g. 🔥 Flash Sale" />
            </div>
            <div>
              <label className="text-neutral-400 text-xs uppercase tracking-wide block mb-1">
                Sale Price {selectedProduct ? (selectedProduct.type === 'EA' ? '(USD $)' : '(₹ INR)') : ''}
              </label>
              <input type="number" value={form.offer_price} onChange={e => setForm(f => ({ ...f, offer_price: e.target.value }))}
                className="w-full bg-neutral-800 border border-neutral-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-orange-500"
                placeholder={selectedProduct?.type === 'EA' ? 'e.g. 300' : 'e.g. 800'} />
              {selectedProduct && form.offer_price && (
                <p className="text-xs text-orange-400 mt-1">
                  Discount: {selectedProduct.type === 'EA'
                    ? `$${selectedProduct.price} → $${form.offer_price}`
                    : `₹${selectedProduct.price.toLocaleString('en-IN')} → ₹${parseFloat(form.offer_price).toLocaleString('en-IN')}`}
                </p>
              )}
            </div>
            <div>
              <label className="text-neutral-400 text-xs uppercase tracking-wide block mb-1">Starts At (IST)</label>
              <input type="datetime-local" value={form.starts_at} onChange={e => setForm(f => ({ ...f, starts_at: e.target.value }))}
                className="w-full bg-neutral-800 border border-neutral-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-orange-500" />
            </div>
            <div>
              <label className="text-neutral-400 text-xs uppercase tracking-wide block mb-1">Expires At (IST)</label>
              <input type="datetime-local" value={form.expires_at} onChange={e => setForm(f => ({ ...f, expires_at: e.target.value }))}
                className="w-full bg-neutral-800 border border-neutral-700 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-orange-500" />
            </div>
          </div>
          <div className="flex gap-3 pt-2">
            <button onClick={() => createMutation.mutate()} disabled={createMutation.isPending || !form.product_id || !form.offer_price || !form.expires_at}
              className="flex items-center gap-2 px-5 py-2 bg-orange-500 hover:bg-orange-400 disabled:opacity-50 text-white rounded-lg font-medium transition-colors text-sm">
              {createMutation.isPending ? <Loader2 size={16} className="animate-spin" /> : <Plus size={16} />} Create Offer
            </button>
            <button onClick={() => setShowForm(false)} className="px-5 py-2 text-neutral-400 hover:text-white transition-colors text-sm">Cancel</button>
          </div>
        </div>
      )}

      {/* Offers List */}
      {isLoading ? (
        <div className="flex justify-center py-12"><Loader2 className="animate-spin text-orange-400" size={32} /></div>
      ) : offers.length === 0 ? (
        <div className="bg-neutral-900 border border-neutral-800 rounded-xl p-12 text-center">
          <Tag size={40} className="text-neutral-600 mx-auto mb-3" />
          <p className="text-neutral-400">No offers yet. Create your first flash sale!</p>
        </div>
      ) : (
        <div className="space-y-3">
          {offers.map((offer: any) => {
            const product = products.find((p: any) => p.id === offer.product_id);
            const active = isActive(offer);
            const expired = new Date(offer.expires_at) < new Date();
            return (
              <div key={offer.id} className={`bg-neutral-900 border rounded-xl p-4 flex flex-col sm:flex-row sm:items-center justify-between gap-4 ${active ? 'border-orange-500/40' : expired ? 'border-neutral-800 opacity-60' : 'border-neutral-800'}`}>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap mb-2">
                    <span className="text-white font-semibold text-base">{offer.offer_label}</span>
                    {active && <span className="px-2 py-0.5 bg-orange-500/10 text-orange-400 border border-orange-500/20 rounded text-xs font-medium">🔥 LIVE</span>}
                    {expired && <span className="px-2 py-0.5 bg-neutral-700/50 text-neutral-500 border border-neutral-700 rounded text-xs font-medium">Expired</span>}
                    {!active && !expired && offer.active && <span className="px-2 py-0.5 bg-blue-500/10 text-blue-400 border border-blue-500/20 rounded text-xs font-medium">Scheduled</span>}
                    {!offer.active && <span className="px-2 py-0.5 bg-neutral-700/50 text-neutral-500 border border-neutral-700 rounded text-xs font-medium">Disabled</span>}
                  </div>
                  <p className="text-neutral-300 text-sm font-medium">
                    {product?.type} — {product?.name}
                  </p>
                  <div className="flex items-center gap-2 mt-0.5 text-sm">
                    <span className="line-through text-neutral-500">{product?.type === 'EA' ? `$${product?.price}` : `₹${product?.price?.toLocaleString('en-IN')}`}</span>
                    <ArrowRight size={14} className="text-neutral-500" />
                    <span className="text-orange-400 font-bold">{product?.type === 'EA' ? `$${offer.offer_price}` : `₹${offer.offer_price?.toLocaleString('en-IN')}`}</span>
                  </div>
                  <p className="text-neutral-500 text-xs mt-2.5 font-mono bg-neutral-950/50 inline-block px-2 py-1 rounded border border-neutral-800/50">
                    {formatDate(offer.starts_at)} <span className="text-neutral-600 px-1">to</span> {formatDate(offer.expires_at)}
                  </p>
                </div>
                <div className="flex items-center justify-end sm:justify-start gap-4 shrink-0 border-t sm:border-t-0 border-neutral-800 pt-3 sm:pt-0 mt-1 sm:mt-0">
                  <button onClick={() => toggleMutation.mutate({ id: offer.id, active: !offer.active })}
                    className={`flex items-center gap-2 transition-colors ${offer.active ? 'text-orange-400 hover:text-orange-300' : 'text-neutral-500 hover:text-white'}`}
                    title={offer.active ? 'Disable' : 'Enable'}>
                    <span className="text-xs font-medium sm:hidden">{offer.active ? 'Active' : 'Disabled'}</span>
                    {offer.active ? <ToggleRight size={28} /> : <ToggleLeft size={28} />}
                  </button>
                  <div className="w-px h-6 bg-neutral-800 hidden sm:block"></div>
                  <button onClick={() => deleteMutation.mutate(offer.id)} className="flex items-center gap-2 text-red-500/60 hover:text-red-400 transition-colors p-1 rounded-md hover:bg-red-500/10">
                    <Trash2 size={18} />
                  </button>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
