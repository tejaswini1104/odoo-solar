import React from 'react';
import {
  LayoutDashboard,
  UserCheck,
  Users,
  Compass,
  Package,
  FileSpreadsheet,
  ShoppingCart,
  Truck,
  Wrench,
  ShieldCheck,
  LifeBuoy,
  Receipt,
  TrendingUp,
  Sun
} from 'lucide-react';

const navItems = [
  { id: 'dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { id: 'leads', label: 'Leads', icon: UserCheck },
  { id: 'customers', label: 'Customers', icon: Users },
  { id: 'surveys', label: 'Site Surveys', icon: Compass },
  { id: 'packages', label: 'Solar Packages', icon: Package },
  { id: 'quotations', label: 'Quotations', icon: FileSpreadsheet },
  { id: 'orders', label: 'Sales Orders', icon: ShoppingCart },
  { id: 'dispatch', label: 'Dispatch & Serials', icon: Truck },
  { id: 'installations', label: 'Installations', icon: Wrench },
  { id: 'warranties', label: 'Warranties', icon: ShieldCheck },
  { id: 'tickets', label: 'Service Tickets', icon: LifeBuoy },
  { id: 'invoices', label: 'Invoices', icon: Receipt },
  { id: 'profitability', label: 'Profitability', icon: TrendingUp },
];

export default function Sidebar({ activeTab, setActiveTab }) {
  return (
    <aside className="w-64 bg-slate-900 text-slate-300 flex flex-col shrink-0 min-h-screen border-r border-slate-800 select-none">
      {/* Brand Header */}
      <div className="h-16 flex items-center gap-3 px-6 border-b border-slate-800 bg-slate-950/40">
        <div className="p-2 bg-gradient-to-tr from-amber-500 to-amber-300 rounded-lg text-slate-950 shadow-md">
          <Sun className="w-5 h-5 fill-current" />
        </div>
        <div>
          <h1 className="text-base font-bold text-white tracking-wide">SunPower ERP</h1>
          <p className="text-[10px] text-amber-400 font-semibold uppercase tracking-wider">Phase 1 Vertical Slice</p>
        </div>
      </div>

      {/* Navigation Links */}
      <nav className="flex-1 px-3 py-4 space-y-1 overflow-y-auto">
        <div className="px-3 pb-2 text-[11px] font-bold text-slate-500 uppercase tracking-wider">
          Operations & Lifecycle
        </div>
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActiveTab(item.id)}
              className={`w-full flex items-center gap-3 px-3.5 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                isActive
                  ? 'bg-amber-500 text-slate-950 shadow-sm font-semibold'
                  : 'text-slate-300 hover:bg-slate-800/80 hover:text-white'
              }`}
            >
              <Icon className={`w-4 h-4 ${isActive ? 'text-slate-950' : 'text-slate-400'}`} />
              <span>{item.label}</span>
            </button>
          );
        })}
      </nav>

      {/* Implicit Admin User info */}
      <div className="p-4 border-t border-slate-800 bg-slate-950/20 text-xs">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-slate-700 flex items-center justify-center font-bold text-amber-400 text-xs">
            AD
          </div>
          <div className="overflow-hidden">
            <p className="font-semibold text-slate-200 truncate">Admin (Single User)</p>
            <p className="text-slate-400 text-[11px]">Operations & Management</p>
          </div>
        </div>
      </div>
    </aside>
  );
}
