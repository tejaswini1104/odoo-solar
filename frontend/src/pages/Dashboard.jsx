import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import { LoadingState, ErrorState } from '../components/States';
import DirectorView from '../components/DirectorView';
import {
  UserCheck,
  Compass,
  ShoppingCart,
  LifeBuoy,
  ShieldCheck
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
      subtext: 'Open or in-progress service tickets'
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

      <DirectorView />
    </div>
  );
}
