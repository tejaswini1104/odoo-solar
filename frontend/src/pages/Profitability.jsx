import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import DataTable from '../components/DataTable';
import StatusBadge from '../components/StatusBadge';
import { LoadingState, ErrorState } from '../components/States';
import { TrendingUp, DollarSign, Wallet, ArrowUpRight, BarChart2 } from 'lucide-react';

export default function Profitability() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchProfitability = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await api.getProfitability();
      setData(res);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProfitability();
  }, []);

  const totalRevenue = data.reduce((acc, row) => acc + (row.revenue || 0), 0);
  const totalCost = data.reduce((acc, row) => acc + (row.total_cost || 0), 0);
  const totalProfit = data.reduce((acc, row) => acc + (row.profit || 0), 0);
  const overallMargin = totalRevenue > 0 ? ((totalProfit / totalRevenue) * 100).toFixed(1) : 0;

  const columns = [
    {
      header: 'Order & Customer',
      accessor: 'order_id',
      render: (row) => (
        <div>
          <span className="font-mono text-xs font-bold text-slate-800">SO-{row.order_id.toString().padStart(4, '0')}</span>
          <div className="font-semibold text-slate-900 mt-0.5">{row.customer_name}</div>
        </div>
      )
    },
    {
      header: 'System Package',
      accessor: 'package_name',
      render: (row) => <span className="text-xs font-medium text-slate-800">{row.package_name}</span>
    },
    {
      header: 'Revenue (excl. GST)',
      accessor: 'revenue',
      render: (row) => <span className="text-xs font-bold text-slate-900">₹{row.revenue?.toLocaleString()}</span>
    },
    {
      header: 'Material Cost',
      accessor: 'material_cost',
      render: (row) => (
        <span className="text-xs font-medium text-slate-700">₹{row.material_cost?.toLocaleString()}</span>
      )
    },
    {
      header: 'Labour Cost',
      accessor: 'labour_cost',
      render: (row) => (
        <span className="text-xs text-slate-600">₹{row.labour_cost?.toLocaleString()}</span>
      )
    },
    {
      header: 'Total Cost',
      accessor: 'total_cost',
      render: (row) => (
        <span className="text-xs font-semibold text-slate-800">₹{row.total_cost?.toLocaleString()}</span>
      )
    },
    {
      header: 'Net Profit & Margin',
      accessor: 'profit',
      render: (row) => {
        const isPositive = row.profit >= 0;
        return (
          <div className="text-xs">
            <div className={`font-extrabold ${isPositive ? 'text-emerald-700' : 'text-rose-700'}`}>
              ₹{row.profit?.toLocaleString()}
            </div>
            <span className={`inline-block mt-0.5 text-[10px] font-bold px-1.5 py-0.5 rounded ${isPositive ? 'bg-emerald-50 text-emerald-700' : 'bg-rose-50 text-rose-700'}`}>
              {row.profit_margin_pct}% Margin
            </span>
          </div>
        );
      }
    },
    {
      header: 'Order Status',
      accessor: 'status',
      render: (row) => <StatusBadge status={row.status} />
    }
  ];

  if (loading) return <LoadingState message="Calculating order profit margins..." />;
  if (error) return <ErrorState title="Failed to calculate profitability" message={error} onRetry={fetchProfitability} />;

  return (
    <div className="space-y-6">
      {/* High-level Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-4 gap-4">
        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <span className="text-xs font-semibold text-slate-500 uppercase">Gross Revenue</span>
          <div className="text-2xl font-black text-slate-900 mt-1">₹{totalRevenue.toLocaleString()}</div>
          <span className="text-[11px] text-slate-400">Completed orders, excl. GST</span>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <span className="text-xs font-semibold text-slate-500 uppercase">Total Project Costs</span>
          <div className="text-2xl font-black text-slate-700 mt-1">₹{totalCost.toLocaleString()}</div>
          <span className="text-[11px] text-slate-400">Dispatched units + BOM bulk items + labour</span>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <span className="text-xs font-semibold text-slate-500 uppercase">Net Realized Profit</span>
          <div className="text-2xl font-black text-emerald-600 mt-1">₹{totalProfit.toLocaleString()}</div>
          <span className="text-[11px] text-emerald-700 font-medium">Revenue - All costs</span>
        </div>

        <div className="bg-white p-4 rounded-xl border border-slate-200 shadow-xs">
          <span className="text-xs font-semibold text-slate-500 uppercase">Average Margin</span>
          <div className="text-2xl font-black text-amber-600 mt-1">{overallMargin}%</div>
          <span className="text-[11px] text-amber-700 font-medium">Across completed jobs</span>
        </div>
      </div>

      <div>
        <h3 className="text-lg font-bold text-slate-900">Per-Order Profitability Table</h3>
        <p className="text-xs text-slate-500">
          Revenue excludes GST. Material cost is the cost of serialized units dispatched on each order plus bulk BOM items; labour is the flat labour cost. Completed installations only.
        </p>
      </div>

      <DataTable
        columns={columns}
        data={data}
        searchPlaceholder="Search order profitability by customer or package..."
        emptyTitle="No completed orders found"
        emptyDescription="Complete customer installations to view realized margins and costs."
      />
    </div>
  );
}
