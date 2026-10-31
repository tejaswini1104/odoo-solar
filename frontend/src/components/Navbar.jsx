import React from 'react';
import { ShieldCheck, HardDrive, BellRing, Database } from 'lucide-react';

export default function Navbar({ activeTitle }) {
  return (
    <header className="h-16 bg-white border-b border-slate-200 px-8 flex items-center justify-between shrink-0 shadow-xs">
      <div className="flex items-center gap-3">
        <h2 className="text-xl font-bold text-slate-800 capitalize tracking-tight">{activeTitle}</h2>
        <span className="hidden md:inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-amber-50 text-amber-800 border border-amber-200">
          Solar Installation Management System
        </span>
      </div>

      <div className="flex items-center gap-4">
        {/* PostgreSQL Connected indicator */}
        <div className="flex items-center gap-1.5 px-3 py-1 bg-emerald-50 text-emerald-700 text-xs font-medium rounded-full border border-emerald-200">
          <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
          <span>PostgreSQL Live</span>
        </div>

        {/* Local disk media indicator */}
        <div className="hidden sm:flex items-center gap-1.5 px-3 py-1 bg-slate-100 text-slate-700 text-xs font-medium rounded-full border border-slate-200">
          <HardDrive className="w-3.5 h-3.5 text-slate-500" />
          <span>Local Media (Disk)</span>
        </div>
      </div>
    </header>
  );
}
