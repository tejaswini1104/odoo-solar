import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import { LoadingState, ErrorState } from '../components/States';
import {
  UserCheck,
  Compass,
  ShoppingCart,
  LifeBuoy,
  ShieldCheck,
  ArrowRight,
  CheckCircle2,
  AlertTriangle,
  Receipt,
  Truck
} from 'lucide-react';

export default function Dashboard({ setActiveTab }) {
  const [metrics, setMetrics] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchMetrics = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.getDashboard();
      setMetrics(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMetrics();
  }, []);

  if (loading) return <LoadingState message="Loading SunPower operations dashboard..." />;
  if (error) return <ErrorState title="Dashboard Error" message={error} onRetry={fetchMetrics} />;

  const cards = [
    {
      title: 'Total Leads',
      value: metrics.total_leads,
      icon: UserCheck,
      color: 'text-blue-600',
      bg: 'bg-blue-50',
      tab: 'leads',
      subtext: 'Enquiries via Web/WhatsApp/Call'
    },
    {
      title: 'Pending Surveys',
      value: metrics.pending_surveys,
      icon: Compass,
      color: 'text-amber-600',
      bg: 'bg-amber-50',
      tab: 'surveys',
      subtext: 'Awaiting technician or approval'
    },
    {
      title: 'Confirmed Orders',
      value: metrics.confirmed_orders,
      icon: ShoppingCart,
      color: 'text-emerald-600',
      bg: 'bg-emerald-50',
      tab: 'orders',
      subtext: 'Active installation pipeline'
    },
    {
      title: 'Open Tickets',
      value: metrics.open_tickets,
      icon: LifeBuoy,
      color: 'text-rose-600',
      bg: 'bg-rose-50',
      tab: 'tickets',
      subtext: 'Customer breakdown calls'
    },
    {
      title: 'Active Warranties',
      value: metrics.active_warranties,
      icon: ShieldCheck,
      color: 'text-teal-600',
      bg: 'bg-teal-50',
      tab: 'warranties',
      subtext: 'Protected solar systems'
    },
  ];

  return (
    <div className="space-y-6">
      {/* 5 KPI Metric Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        {cards.map((card, idx) => {
          const Icon = card.icon;
          return (
            <div
              key={idx}
              onClick={() => setActiveTab(card.tab)}
              className="bg-white p-5 rounded-xl border border-slate-200 shadow-xs hover:border-slate-300 hover:shadow-md transition cursor-pointer flex flex-col justify-between"
            >
              <div className="flex items-center justify-between">
                <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">{card.title}</span>
                <div className={`p-2 rounded-lg ${card.bg}`}>
                  <Icon className={`w-5 h-5 ${card.color}`} />
                </div>
              </div>
              <div className="mt-3">
                <div className="text-3xl font-extrabold text-slate-900">{card.value}</div>
                <div className="text-xs text-slate-500 mt-1">{card.subtext}</div>
              </div>
            </div>
          );
        })}
      </div>

      {/* Phase 1 Walkthrough & Verification Panel */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-xs p-6">
        <div className="flex items-center justify-between pb-4 border-b border-slate-100">
          <div>
            <h3 className="text-base font-bold text-slate-900">Phase 1 Operational Vertical Slice</h3>
            <p className="text-xs text-slate-500 mt-0.5">
              Strict end-to-end flow with enforced backend hard gates, inventory reservation, and warranty automation.
            </p>
          </div>
          <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-emerald-100 text-emerald-800">
            Seeded & Verified
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-6">
          {/* Box 1: Hard Gates */}
          <div className="bg-slate-50 p-4 rounded-lg border border-slate-200">
            <h4 className="text-sm font-semibold text-slate-800 flex items-center gap-2 mb-3">
              <AlertTriangle className="w-4 h-4 text-amber-500" /> Enforced Hard Gates
            </h4>
            <ul className="text-xs space-y-2 text-slate-600">
              <li className="flex items-start gap-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0 mt-0.5" />
                <span><strong>Quotation Blocked:</strong> Cannot create quote without Approved site survey.</span>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0 mt-0.5" />
                <span><strong>Order Confirm Gate:</strong> Requires approved survey + advance payment recorded.</span>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0 mt-0.5" />
                <span><strong>Dispatch Validation:</strong> DB-level unique serial constraint + in-stock check.</span>
              </li>
              <li className="flex items-start gap-2">
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600 shrink-0 mt-0.5" />
                <span><strong>Ticket Closure Gate:</strong> Blocked without customer confirmation flag.</span>
              </li>
            </ul>
          </div>

          {/* Box 2: Automated Engines */}
          <div className="bg-slate-50 p-4 rounded-lg border border-slate-200">
            <h4 className="text-sm font-semibold text-slate-800 flex items-center gap-2 mb-3">
              <CheckCircle2 className="w-4 h-4 text-emerald-600" /> Automated Backend Engines
            </h4>
            <ul className="text-xs space-y-2 text-slate-600">
              <li className="flex items-start gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-500 shrink-0 mt-1.5" />
                <span><strong>Auto-BOM:</strong> Package components automatically convert to quotation line items.</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-500 shrink-0 mt-1.5" />
                <span><strong>Atomic Order Confirm:</strong> Reserves stock + creates installation job + assigns tech.</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-500 shrink-0 mt-1.5" />
                <span><strong>Warranty Engine:</strong> On complete: auto 24mo for Inverter/Battery + 240mo bulk panel warranty.</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-amber-500 shrink-0 mt-1.5" />
                <span><strong>Warranty Decision:</strong> Ticket evaluates Active (COVERED ₹0) vs Expired (BILLABLE + Draft invoice).</span>
              </li>
            </ul>
          </div>

          {/* Box 3: Seed Scenarios */}
          <div className="bg-slate-50 p-4 rounded-lg border border-slate-200">
            <h4 className="text-sm font-semibold text-slate-800 flex items-center gap-2 mb-3">
              <Receipt className="w-4 h-4 text-blue-600" /> Seed Data Scenarios
            </h4>
            <div className="space-y-3 text-xs">
              <div className="p-2.5 bg-emerald-50 border border-emerald-200 rounded text-emerald-900">
                <div className="font-bold flex justify-between">
                  <span>Ravi Kumar (Hyderabad)</span>
                  <span className="text-[10px] bg-emerald-200 px-1.5 py-0.5 rounded font-mono">INV-2026-0042</span>
                </div>
                <div className="text-[11px] mt-1 text-emerald-700">
                  5kW On-Grid. Installed recently. Ticket resolves to <strong>COVERED (₹0)</strong>.
                </div>
              </div>

              <div className="p-2.5 bg-rose-50 border border-rose-200 rounded text-rose-900">
                <div className="font-bold flex justify-between">
                  <span>Anand Sharma (Bengaluru)</span>
                  <span className="text-[10px] bg-rose-200 px-1.5 py-0.5 rounded font-mono">INV-2023-0018</span>
                </div>
                <div className="text-[11px] mt-1 text-rose-700">
                  Installed Jan 2023. Warranty expired Jan 2025. Ticket resolves to <strong>BILLABLE (₹7,080 Draft Invoice)</strong>.
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Quick navigation flow */}
        <div className="mt-6 pt-5 border-t border-slate-100 flex flex-wrap items-center justify-between gap-3">
          <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">Quick Jump to Modules:</span>
          <div className="flex flex-wrap gap-2">
            <button
              onClick={() => setActiveTab('surveys')}
              className="px-3 py-1.5 text-xs font-medium rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 transition"
            >
              1. Site Surveys
            </button>
            <button
              onClick={() => setActiveTab('quotations')}
              className="px-3 py-1.5 text-xs font-medium rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 transition"
            >
              2. Quotations (Auto-BOM)
            </button>
            <button
              onClick={() => setActiveTab('orders')}
              className="px-3 py-1.5 text-xs font-medium rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 transition"
            >
              3. Sales Orders & Payments
            </button>
            <button
              onClick={() => setActiveTab('dispatch')}
              className="px-3 py-1.5 text-xs font-medium rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 transition"
            >
              4. Dispatch Serials
            </button>
            <button
              onClick={() => setActiveTab('installations')}
              className="px-3 py-1.5 text-xs font-medium rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 transition"
            >
              5. Installations & Warranty Engine
            </button>
            <button
              onClick={() => setActiveTab('tickets')}
              className="px-3 py-1.5 text-xs font-medium rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 transition"
            >
              6. Service Tickets
            </button>
            <button
              onClick={() => setActiveTab('profitability')}
              className="px-3 py-1.5 text-xs font-medium rounded-lg bg-amber-100 hover:bg-amber-200 text-amber-900 font-semibold transition"
            >
              7. Profitability Table
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
