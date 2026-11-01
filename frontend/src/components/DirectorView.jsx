import React, { useEffect, useState } from 'react';
import { Download, Printer } from 'lucide-react';
import { api } from '../api/client';
import { LoadingState, ErrorState } from './States';
import { localIsoDate, monthStartIso } from '../utils/dates';

const rupees = (n) => `₹${Number(n || 0).toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;
const PERIODS = [
  { key: 'today', label: 'Today' },
  { key: 'week', label: 'This week' },
  { key: 'month', label: 'This month' },
  { key: 'custom', label: 'Choose dates' },
];

function Tile({ title, value, hint, tone = 'slate' }) {
  const tones = { slate: 'text-slate-900', green: 'text-emerald-700', red: 'text-rose-700' };
  return (
    <div className="bg-white border border-slate-200 rounded-xl p-4">
      <div className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">{title}</div>
      <div className={`text-2xl font-extrabold mt-1 ${tones[tone]}`}>{value}</div>
      {hint && <div className="text-[11px] text-slate-400 mt-0.5">{hint}</div>}
    </div>
  );
}

// The director's picture of the company: what happened, what it earned, and what is still unfinished.
export default function DirectorView() {
  const [period, setPeriod] = useState('month');
  const [from, setFrom] = useState(monthStartIso());
  const [to, setTo] = useState(localIsoDate());
  const [summary, setSummary] = useState(null);
  const [jobs, setJobs] = useState([]);
  const [pipeline, setPipeline] = useState([]);
  const [kind, setKind] = useState('All');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = async (nextPeriod = period) => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.getReportSummary(nextPeriod, from, to);
      const [rows, open] = await Promise.all([
        api.getProfitabilityRange(data.period.from, data.period.to),
        api.getPipeline(),
      ]);
      setSummary(data);
      setJobs(rows);
      setPipeline(open);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const choose = (key) => {
    setPeriod(key);
    if (key !== 'custom') load(key);
  };

  const query = period === 'custom' ? `period=custom&from=${from}&to=${to}` : `period=${period}`;
  const kinds = ['All', ...Array.from(new Set(pipeline.map((p) => p.kind)))];
  const shown = kind === 'All' ? pipeline : pipeline.filter((p) => p.kind === kind);

  return (
    <section className="space-y-5">
      <div className="flex flex-col lg:flex-row lg:items-end justify-between gap-3 print:hidden">
        <div>
          <h3 className="text-lg font-bold text-slate-900">Director's view</h3>
          <p className="text-xs text-slate-500">How the company is doing, what each job earned, and what is still unfinished.</p>
        </div>
        <div className="flex flex-wrap items-end gap-2 text-xs">
          <div className="inline-flex rounded-lg border border-slate-300 overflow-hidden">
            {PERIODS.map((p) => (
              <button
                key={p.key}
                onClick={() => choose(p.key)}
                className={`px-3 py-2 font-semibold ${period === p.key ? 'bg-slate-900 text-white' : 'bg-white text-slate-700 hover:bg-slate-100'}`}
              >
                {p.label}
              </button>
            ))}
          </div>
          {period === 'custom' && (
            <>
              <input type="date" value={from} max={to} onChange={(e) => setFrom(e.target.value)} className="px-2.5 py-1.5 border border-slate-300 rounded-lg" />
              <input type="date" value={to} min={from} max={localIsoDate()} onChange={(e) => setTo(e.target.value)} className="px-2.5 py-1.5 border border-slate-300 rounded-lg" />
              <button onClick={() => load('custom')} className="px-3 py-2 bg-amber-500 text-slate-950 rounded-lg font-semibold hover:bg-amber-600">Show</button>
            </>
          )}
          <a href={`/api/reports/summary.csv?${query}`} className="inline-flex items-center gap-1.5 px-3 py-2 border border-slate-300 rounded-lg font-semibold text-slate-700 hover:bg-slate-100">
            <Download className="w-3.5 h-3.5" /> Download figures
          </a>
          <button onClick={() => window.print()} className="inline-flex items-center gap-1.5 px-3 py-2 border border-slate-300 rounded-lg font-semibold text-slate-700 hover:bg-slate-100">
            <Printer className="w-3.5 h-3.5" /> Print
          </button>
        </div>
      </div>

      {loading ? (
        <LoadingState message="Gathering the figures..." />
      ) : error ? (
        <ErrorState title="Could not load the director's view" message={error} onRetry={() => load()} />
      ) : (
        <>
          <p className="text-sm font-semibold text-slate-700">{summary.period.label}</p>

          <div>
            <h4 className="text-xs font-bold uppercase tracking-wide text-slate-500 mb-2">What happened</h4>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <Tile title="New leads" value={summary.activity.new_leads} />
              <Tile title="Surveys scheduled" value={summary.activity.surveys_scheduled} />
              <Tile title="Quotations made" value={summary.activity.quotations_created} />
              <Tile title="Orders placed" value={summary.activity.orders_placed} />
              <Tile title="Deliveries" value={summary.activity.deliveries} />
              <Tile title="Installations done" value={summary.activity.installations_completed} />
              <Tile title="Repairs opened" value={summary.activity.tickets_opened} />
              <Tile title="Repairs resolved" value={summary.activity.tickets_resolved} />
            </div>
          </div>

          <div>
            <h4 className="text-xs font-bold uppercase tracking-wide text-slate-500 mb-2">Money</h4>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <Tile title="Cash received" value={rupees(summary.money.cash_received)} hint="verified payments" tone="green" />
              <Tile title="Invoices paid" value={rupees(summary.money.invoices_paid_total)} hint={`${summary.money.invoices_paid_count} invoice(s)`} />
              <Tile title="Stock bought" value={rupees(summary.money.stock_spend)} hint="supplier purchases" />
              <Tile title="Technician pay" value={rupees(summary.money.technician_pay_paid)} hint="paid out" />
            </div>
          </div>

          <div>
            <h4 className="text-xs font-bold uppercase tracking-wide text-slate-500 mb-2">Profit on jobs finished</h4>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <Tile title="Jobs finished" value={summary.profit.jobs} hint={summary.profit.losing_jobs ? `${summary.profit.losing_jobs} lost money` : 'none lost money'} tone={summary.profit.losing_jobs ? 'red' : 'slate'} />
              <Tile title="Revenue" value={rupees(summary.profit.revenue)} hint="excluding GST" />
              <Tile title="Costs" value={rupees(summary.profit.material_cost + summary.profit.labour_cost)} hint={`materials ${rupees(summary.profit.material_cost)}, labour ${rupees(summary.profit.labour_cost)}`} />
              <Tile title="Profit" value={rupees(summary.profit.profit)} hint={`${summary.profit.margin_pct}% margin`} tone={summary.profit.profit < 0 ? 'red' : 'green'} />
            </div>
          </div>

          <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
            <div className="px-4 py-3 border-b border-slate-200 flex items-center justify-between">
              <h4 className="text-sm font-bold text-slate-900">Profit on each job finished in this period</h4>
              <a href={`/api/reports/profitability.csv?from=${summary.period.from}&to=${summary.period.to}`} className="text-xs font-semibold text-slate-700 hover:underline print:hidden">Download</a>
            </div>
            {jobs.length === 0 ? (
              <p className="p-4 text-xs text-slate-500">No job was finished in this period.</p>
            ) : (
              <table className="w-full text-xs">
                <thead className="bg-slate-50 text-slate-500 text-left">
                  <tr>
                    <th className="px-4 py-2">Job</th><th className="px-4 py-2">Finished</th>
                    <th className="px-4 py-2 text-right">Revenue</th><th className="px-4 py-2 text-right">Materials</th>
                    <th className="px-4 py-2 text-right">Labour</th><th className="px-4 py-2 text-right">Profit</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {jobs.map((job) => (
                    <tr key={job.order_id}>
                      <td className="px-4 py-2"><div className="font-semibold text-slate-900">{job.customer_name}</div><div className="text-slate-500">SO-{String(job.order_id).padStart(4, '0')} · {job.package_name}</div></td>
                      <td className="px-4 py-2">{job.finished_on ? new Date(job.finished_on).toLocaleDateString('en-IN') : '-'}</td>
                      <td className="px-4 py-2 text-right">{rupees(job.revenue)}</td>
                      <td className="px-4 py-2 text-right">{rupees(job.material_cost)}</td>
                      <td className="px-4 py-2 text-right"><div>{rupees(job.labour_cost)}</div><div className="text-[10px] text-slate-400">{job.labour_basis}</div></td>
                      <td className={`px-4 py-2 text-right font-bold ${job.profit < 0 ? 'text-rose-700' : 'text-emerald-700'}`}>{rupees(job.profit)}<div className="text-[10px] font-normal text-slate-400">{job.profit_margin_pct}%</div></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>

          <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
            <div className="px-4 py-3 border-b border-slate-200 flex flex-wrap items-center justify-between gap-2">
              <div>
                <h4 className="text-sm font-bold text-slate-900">What is still unfinished</h4>
                <p className="text-[11px] text-slate-500">
                  {summary.open_now.orders_awaiting_advance} order(s) awaiting the advance · {summary.open_now.jobs_in_progress} installation(s) in progress ·
                  {' '}{summary.open_now.repairs_open} repair(s) open · {summary.open_now.subsidies_open} subsidy file(s) open · technicians are owed {rupees(summary.open_now.technician_pay_due)}
                </p>
              </div>
              <div className="flex items-center gap-2 print:hidden">
                <select value={kind} onChange={(e) => setKind(e.target.value)} className="text-xs border border-slate-300 rounded-lg px-2 py-1.5 bg-white">
                  {kinds.map((k) => <option key={k}>{k}</option>)}
                </select>
                <a href="/api/reports/pipeline.csv" className="text-xs font-semibold text-slate-700 hover:underline">Download</a>
              </div>
            </div>
            {shown.length === 0 ? (
              <p className="p-4 text-xs text-slate-500">Nothing is waiting. Every job is finished.</p>
            ) : (
              <table className="w-full text-xs">
                <thead className="bg-slate-50 text-slate-500 text-left">
                  <tr>
                    <th className="px-4 py-2">Item</th><th className="px-4 py-2">Stage</th>
                    <th className="px-4 py-2">Waiting for</th><th className="px-4 py-2 text-right">Days</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {shown.map((row) => (
                    <tr key={`${row.kind}-${row.reference}`}>
                      <td className="px-4 py-2"><div className="font-semibold text-slate-900">{row.customer}</div><div className="text-slate-500"><span className="font-mono">{row.reference}</span> · {row.detail}</div></td>
                      <td className="px-4 py-2 text-slate-800">{row.stage}</td>
                      <td className="px-4 py-2 text-slate-600">{row.next_step}</td>
                      <td className={`px-4 py-2 text-right font-semibold ${row.days_waiting >= 7 ? 'text-rose-700' : 'text-slate-700'}`}>{row.days_waiting}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        </>
      )}
    </section>
  );
}
