'use client';

import { useQuery } from '@tanstack/react-query';
import { Package, Plus, Loader2, Edit, Trash2 } from 'lucide-react';
import api from '@/lib/api';

export default function ProductsPage() {
  const { data: products = [], isLoading, error } = useQuery({
    queryKey: ['admin-products'],
    queryFn: async () => {
      const { data } = await api.get('/api/v1/admin/products');
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

  if (error) {
    return (
      <div className="bg-red-500/10 border border-red-500/20 text-red-400 p-4 rounded-lg">
        Failed to load products.
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Products</h1>
          <p className="text-neutral-400 mt-1">Manage trading bots and VPS packages.</p>
        </div>
        <button className="flex items-center px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white rounded-lg font-medium transition-colors">
          <Plus size={18} className="mr-2" />
          Add Product
        </button>
      </div>

      <div className="bg-neutral-900 border border-neutral-800 rounded-xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm text-left">
            <thead className="text-xs text-neutral-400 bg-neutral-900/50 uppercase border-b border-neutral-800">
              <tr>
                <th className="px-6 py-4">Name</th>
                <th className="px-6 py-4">Type</th>
                <th className="px-6 py-4">Price (₹)</th>
                <th className="px-6 py-4">Status</th>
                <th className="px-6 py-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-800">
              {products.length === 0 ? (
                <tr>
                  <td colSpan={5} className="px-6 py-8 text-center text-neutral-500">
                    No products found.
                  </td>
                </tr>
              ) : (
                products.map((product: any) => (
                  <tr key={product.id} className="hover:bg-neutral-800/30 transition-colors">
                    <td className="px-6 py-4">
                      <div className="flex items-center">
                        <div className="h-8 w-8 rounded bg-neutral-800 flex items-center justify-center mr-3">
                          <Package size={16} className="text-neutral-400" />
                        </div>
                        <span className="font-medium text-white">{product.name}</span>
                      </div>
                    </td>
                    <td className="px-6 py-4 text-neutral-400 capitalize">{product.type || 'Standard'}</td>
                    <td className="px-6 py-4 text-neutral-300">₹{product.price?.toLocaleString() || 0}</td>
                    <td className="px-6 py-4">
                      <span className="px-2 py-1 bg-emerald-500/10 text-emerald-400 rounded text-xs font-medium border border-emerald-500/20">
                        Active
                      </span>
                    </td>
                    <td className="px-6 py-4 text-right space-x-2">
                      <button className="p-2 text-neutral-400 hover:text-white hover:bg-neutral-700 rounded transition-colors" title="Edit">
                        <Edit size={16} />
                      </button>
                      <button className="p-2 text-neutral-400 hover:text-red-400 hover:bg-red-500/10 rounded transition-colors" title="Delete">
                        <Trash2 size={16} />
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
