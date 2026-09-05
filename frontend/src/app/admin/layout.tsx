'use client';

import { ReactNode, useState, useEffect } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { LayoutDashboard, 
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
  Clock, Settings
, ShieldCheck } from 'lucide-react';

const navigation = [
  { name: 'Dashboard', href: '/admin', icon: LayoutDashboard },
  { name: 'Orders', href: '/admin/orders', icon: ShoppingCart },
  { name: 'Products', href: '/admin/products', icon: Package },
  { name: 'Licenses', href: '/admin/licenses', icon: Key },
  { name: 'EA Approvals', href: '/admin/ea-approvals', icon: ShieldCheck },
  { name: 'Installments', href: '/admin/installments', icon: History },
  { name: 'VPS', href: '/admin/vps', icon: Server },
  { name: 'Compiler', href: '/admin/compiler', icon: Terminal },
  { name: 'EA Template', href: '/admin/ea-template', icon: FileCode2 },
  { name: 'Free Trial', href: '/admin/trial', icon: Gift },
  { name: 'Settings', href: '/admin/settings', icon: Settings },
];

export default function AdminLayout({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);
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


  return (
    <div className="fixed inset-0 bg-black text-white flex overflow-hidden w-full">
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
        <div className="h-16 flex items-center justify-between px-4 md:px-6 border-b border-neutral-800 shrink-0">
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
        
        <nav className="flex-1 overflow-y-auto py-4 md:py-6 px-3 space-y-1 scrollbar-thin scrollbar-thumb-neutral-800 scrollbar-track-transparent pb-10">
          {navigation.map((item) => {
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.name}
                href={item.href}
                className={`flex items-center space-x-3 px-3 py-2 md:py-2.5 text-sm md:text-base rounded-lg transition-colors ${
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

        <div className="p-3 border-t border-neutral-800 shrink-0 pb-8 md:pb-4">
          <button 
            onClick={() => {
              document.cookie = 'admin_token=; path=/; expires=Thu, 01 Jan 1970 00:00:01 GMT;';
              window.location.href = '/login';
            }}
            className="flex items-center space-x-3 px-3 py-2 md:py-2.5 w-full rounded-lg text-sm md:text-base text-red-400 hover:text-red-300 hover:bg-red-500/10 transition-colors"
          >
            <LogOut size={20} />
            <span className="font-medium">Logout</span>
          </button>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 flex flex-col min-w-0 md:relative pt-16 md:pt-0 h-full overflow-hidden">
        {/* Desktop Floating Clock Pill */}
        <div className="hidden md:flex justify-end pt-6 pr-8 pb-0 pointer-events-none">
          {utcTime && (
            <div className="flex items-center gap-2 bg-neutral-900/60 backdrop-blur-xl border border-neutral-700/50 shadow-2xl px-3 py-1.5 rounded-full text-neutral-300 text-xs font-medium font-mono ring-1 ring-white/5">
              <Clock size={13} className="text-blue-400 animate-pulse" />
              <span className="tracking-wide text-neutral-200">
                <span className="text-neutral-500 mr-1">IST</span>
                {utcTime}
              </span>
            </div>
          )}
        </div>
        <main className="flex-1 overflow-y-auto overscroll-y-contain p-4 pb-24 md:px-8 md:pb-8 md:pt-4" style={{ WebkitOverflowScrolling: "touch" }}>
          <div className="h-full">
            {children}
          </div>
        </main>
      </div>
    </div>
  );
}



