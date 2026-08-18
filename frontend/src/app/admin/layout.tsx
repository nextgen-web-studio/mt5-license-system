'use client';

import { ReactNode, useState, useEffect } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { 
  LayoutDashboard, 
  ShoppingCart, 
  Package, 
  Key, 
  Server, 
  Terminal,
  Gift,
  FileCode2,
  LogOut,
  Menu,
  X,
  History,
  Clock
} from 'lucide-react';

const navigation = [
  { name: 'Dashboard', href: '/admin', icon: LayoutDashboard },
  { name: 'Orders', href: '/admin/orders', icon: ShoppingCart },
  { name: 'Products', href: '/admin/products', icon: Package },
  { name: 'Licenses', href: '/admin/licenses', icon: Key },
  { name: 'Installments', href: '/admin/installments', icon: History },
  { name: 'VPS', href: '/admin/vps', icon: Server },
  { name: 'Compiler', href: '/admin/compiler', icon: Terminal },
  { name: 'EA Template', href: '/admin/ea-template', icon: FileCode2 },
  { name: 'Free Trial', href: '/admin/trial', icon: Gift },
];

export default function AdminLayout({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
  const [countdown, setCountdown] = useState(5);
  const [utcTime, setUtcTime] = useState<string>('');

  // IST live clock (UTC+5:30)
  useEffect(() => {
    const tick = () => setUtcTime(
      new Date().toLocaleString('en-GB', {
        timeZone: 'Asia/Kolkata',
        day: '2-digit', month: 'short', year: 'numeric',
        hour: '2-digit', minute: '2-digit', second: '2-digit',
        hour12: false
      })
    );
    tick();
    const interval = setInterval(tick, 1000);
    return () => clearInterval(interval);
  }, []);

  // Close mobile menu when route changes
  useEffect(() => {
    setIsMobileMenuOpen(false);
  }, [pathname]);

  // Auto-refresh countdown display
  useEffect(() => {
    const interval = setInterval(() => {
      setCountdown(prev => {
        if (prev <= 1) return 5;
        return prev - 1;
      });
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="h-screen bg-black text-white flex overflow-hidden">
      {/* Mobile Top Bar */}
      <div className="md:hidden fixed top-0 left-0 right-0 h-16 bg-neutral-900 border-b border-neutral-800 flex items-center justify-between px-4 z-40">
        <div className="flex items-center gap-3">
          <img src="/logo.jpg" alt="Logo" className="w-8 h-8 object-contain" />
          <h1 className="text-xl font-bold text-white">
            Admin Panel
          </h1>
        </div>
        <div className="flex items-center gap-3">

          <button 
            onClick={() => setIsMobileMenuOpen(true)}
            className="text-neutral-400 hover:text-white"
          >
            <Menu size={24} />
          </button>
        </div>
      </div>

      {/* Mobile Sidebar Overlay */}
      {isMobileMenuOpen && (
        <div 
          className="md:hidden fixed inset-0 bg-black/50 z-40"
          onClick={() => setIsMobileMenuOpen(false)}
        />
      )}

      {/* Sidebar */}
      <div 
        className={`fixed md:relative inset-y-0 left-0 z-50 w-64 bg-neutral-900 border-r border-neutral-800 flex flex-col transform transition-transform duration-200 ease-in-out ${
          isMobileMenuOpen ? 'translate-x-0' : '-translate-x-full md:translate-x-0'
        }`}
      >
        <div className="h-16 flex items-center justify-between px-6 border-b border-neutral-800">
          <div className="flex items-center gap-3">
            <img src="/logo.jpg" alt="Logo" className="w-8 h-8 object-contain" />
            <h1 className="text-xl font-bold text-white">
              Admin Panel
            </h1>
          </div>
          <button 
            className="md:hidden text-neutral-400 hover:text-white"
            onClick={() => setIsMobileMenuOpen(false)}
          >
            <X size={24} />
          </button>
        </div>
        
        <nav className="flex-1 overflow-y-auto py-6 px-3 space-y-1">
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

        <div className="p-4 border-t border-neutral-800 shrink-0 space-y-2">
          <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-emerald-500/5 border border-emerald-500/20">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
            </span>
            <span className="text-xs text-emerald-400 font-medium">Live · refreshes in {countdown}s</span>
          </div>
          <button className="flex items-center space-x-3 px-3 py-2.5 w-full rounded-lg text-neutral-400 hover:text-white hover:bg-neutral-800/50 transition-colors">
            <LogOut size={20} />
            <span className="font-medium">Logout</span>
          </button>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 md:relative pt-16 md:pt-0 h-full overflow-hidden">
        {/* Desktop UTC bar */}
        <div className="hidden md:flex items-center justify-end px-8 py-2 border-b border-neutral-800/50 bg-neutral-950/30">
          {utcTime && (
            <div className="flex items-center gap-1.5 bg-neutral-800/50 border border-neutral-700/50 px-2.5 py-1 rounded-md text-neutral-300 text-xs font-mono" title="UTC Time">
              <Clock size={11} className="text-indigo-400" />
              <span>IST: {utcTime}</span>
            </div>
          )}
        </div>
        <main className="flex-1 overflow-y-auto p-4 md:p-8">
          <div className="h-full">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}
