'use client';

import { ReactNode } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { 
  LayoutDashboard, 
  ShoppingCart, 
  Package, 
  Key, 
  Server, 
  Terminal,
  LogOut
} from 'lucide-react';

const navigation = [
  { name: 'Dashboard', href: '/admin', icon: LayoutDashboard },
  { name: 'Orders', href: '/admin/orders', icon: ShoppingCart },
  { name: 'Products', href: '/admin/products', icon: Package },
  { name: 'Licenses', href: '/admin/licenses', icon: Key },
  { name: 'VPS', href: '/admin/vps', icon: Server },
  { name: 'Compiler', href: '/admin/compiler', icon: Terminal },
];

export default function AdminLayout({ children }: { children: ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="min-h-screen bg-black text-white flex">
      {/* Sidebar */}
      <div className="w-64 bg-neutral-900 border-r border-neutral-800 flex flex-col">
        <div className="h-16 flex items-center px-6 border-b border-neutral-800">
          <h1 className="text-xl font-bold bg-gradient-to-r from-blue-400 to-indigo-500 bg-clip-text text-transparent">
            Admin Panel
          </h1>
        </div>
        
        <nav className="flex-1 py-6 px-3 space-y-1">
          {navigation.map((item) => {
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.name}
                href={item.href}
                className={`flex items-center space-x-3 px-3 py-2.5 rounded-lg transition-colors ${
                  isActive 
                    ? 'bg-blue-600/10 text-blue-400' 
                    : 'text-neutral-400 hover:text-white hover:bg-neutral-800/50'
                }`}
              >
                <item.icon size={20} />
                <span className="font-medium">{item.name}</span>
              </Link>
            );
          })}
        </nav>

        <div className="p-4 border-t border-neutral-800">
          <button className="flex items-center space-x-3 px-3 py-2.5 w-full rounded-lg text-neutral-400 hover:text-white hover:bg-neutral-800/50 transition-colors">
            <LogOut size={20} />
            <span className="font-medium">Logout</span>
          </button>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <main className="flex-1 overflow-y-auto p-8">
          {children}
        </main>
      </div>
    </div>
  );
}
