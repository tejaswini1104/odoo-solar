import React, { useEffect, useState } from 'react';
import { Download } from 'lucide-react';
import { api } from '../api/client';
import DataTable from '../components/DataTable';
import Modal from '../components/Modal';
import { LoadingState, ErrorState } from '../components/States';
import { useToast } from '../components/Toast';
import { localIsoDate, monthStartIso } from '../utils/dates';

const rupees = (n) => `₹${Number(n || 0).toLocaleString('en-IN', { maximumFractionDigits: 2 })}`;

// Pay for technicians: hours worked on finished jobs, at each technician's hourly rate.
export default function Payroll() {
  const { addToast } = useToast();
  const [from, setFrom] = useState(monthStartIso());
  const [to, setTo] = useState(localIsoDate());
  const [summary, setSummary] = useState(null);
  const [payouts, setPayouts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [rates, setRates] = useState({});
  const [paying, setPaying] = useState(null);
  const [reference, setReference] = useState('');
  const [busy, setBusy] = useState(false);
  const [payError, setPayError] = useState(null);

  const load = async () => {
    try {
      setLoading(true);
      setError(null);
      const [summaryData, payoutData] = await Promise.all([api.getPayrollSummary(from, to), api.getPayouts()]);
      setSummary(summaryData);
      setPayouts(payoutData);
      setRates(Object.fromEntries(summaryData.rows.map((r) => [r.technician_id, String(r.hourly_rate)])));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const saveRate = async (row) => {
    try {
      await api.setTechnicianRate(row.technician_id, Number(rates[row.technician_id]));
      addToast(`${row.technician_name}'s rate is now ₹${rates[row.technician_id]} an hour.`, 'success');
      load();
    } catch (err) {
      addToast(`Could not change the rate: ${err.message}`, 'error', 6000);
    }
  };

  const confirmPay = async () => {
    setPayError(null);
    try {
      setBusy(true);
      const payout = await api.payTechnician(paying.technician_id, from, to, reference.trim());
      addToast(`Paid ${paying.technician_name} ${rupees(payout.amount)} for ${payout.jobs_count} job${payout.jobs_count === 1 ? '' : 's'}.`, 'success', 6000);
      setPaying(null);
      setReference('');
      load();
    } catch (err) {
      setPayError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const columns = [
    { header: 'Technician', accessor: 'technician_name', render: (r) => <span className="font-semibold text-slate-900 text-xs">{r.technician_name}</span> },
    {
      header: 'Hourly rate',
      accessor: 'hourly_rate',
      render: (r) => (
        <div className="flex items-center gap-1.5">
          <span className="text-xs text-slate-500">₹</span>
          <input
            type="number"
            min="1"
            max="5000"
            value={rates[r.technician_id] ?? ''}
            onChange={(e) => setRates({ ...rates, [r.technician_id]: e.target.value })}
            className="w-20 px-2 py-1 border border-slate-300 rounded text-xs"
          />
          {String(r.hourly_rate) !== rates[r.technician_id] && (
            <button onClick={() => saveRate(r)} className="text-[11px] font-semibold text-amber-700 hover:underline">Save</button>
          )}
        </div>
      )
    },
    {
      header: 'Owed (unpaid jobs)',
      accessor: 'unpaid_jobs',
      render: (r) => (
        <div className="text-xs">
          <div>{r.unpaid_jobs} job{r.unpaid_jobs === 1 ? '' : 's'}, {r.unpaid_hours} h</div>
          {r.jobs_without_hours > 0 && <div className="text-rose-600">{r.jobs_without_hours} job(s) have no recorded hours</div>}
        </div>
      )
    },
    { header: 'Amount due', accessor: 'amount_due', render: (r) => <span className="text-xs font-bold text-slate-900">{rupees(r.amount_due)}</span> },
    { header: 'Already paid', accessor: 'paid_jobs', render: (r) => <span className="text-xs text-slate-600">{r.paid_jobs} job{r.paid_jobs === 1 ? '' : 's'}, {r.paid_hours} h</span> },
    {
      header: 'Action',
      accessor: 'technician_id',
      render: (r) => (
        <button
          disabled={r.unpaid_jobs === 0 || r.amount_due <= 0}
          onClick={() => { setPaying(r); setReference(''); setPayError(null); }}
          className="px-2.5 py-1 text-xs font-semibold rounded bg-emerald-600 hover:bg-emerald-700 text-white transition disabled:opacity-30"
        >
          Record payment
        </button>
      )
    },
  ];

  const payoutColumns = [
    { header: 'Paid on', accessor: 'paid_on', render: (p) => <span className="text-xs">{new Date(`${p.paid_on}Z`).toLocaleDateString('en-IN')}</span> },
    { header: 'Technician', accessor: 'technician_name', render: (p) => <span className="text-xs font-semibold">{p.technician_name}</span> },
    { header: 'Period', accessor: 'period_start', render: (p) => <span className="text-xs">{new Date(p.period_start).toLocaleDateString('en-IN')} to {new Date(p.period_end).toLocaleDateString('en-IN')}</span> },
    { header: 'Work', accessor: 'hours', render: (p) => <span className="text-xs">{p.jobs_count} job(s), {p.hours} h at ₹{p.hourly_rate}</span> },
    { header: 'Amount', accessor: 'amount', render: (p) => <span className="text-xs font-bold">{rupees(p.amount)}</span> },
    { header: 'Reference', accessor: 'reference', render: (p) => <span className="font-mono text-xs">{p.reference || '-'}</span> },
  ];

  return (
    <div className="space-y-6">
      <div className="flex flex-col lg:flex-row justify-between items-start lg:items-end gap-3">
        <div>
          <h3 className="text-lg font-bold text-slate-900">Technician pay</h3>
          <p className="text-xs text-slate-500">
            Pay is hours worked on finished jobs times the technician's hourly rate. A job can be paid only once.
          </p>
        </div>
        <div className="flex flex-wrap items-end gap-2 text-xs">
          <div>
            <label className="block font-semibold text-slate-700 mb-1">Jobs finished from</label>
            <input type="date" value={from} max={to} onChange={(e) => setFrom(e.target.value)} className="px-2.5 py-1.5 border border-slate-300 rounded-lg" />
          </div>
          <div>
            <label className="block font-semibold text-slate-700 mb-1">to</label>
            <input type="date" value={to} min={from} onChange={(e) => setTo(e.target.value)} className="px-2.5 py-1.5 border border-slate-300 rounded-lg" />
          </div>
          <button onClick={load} className="px-3 py-2 bg-slate-900 text-white rounded-lg font-semibold hover:bg-slate-800">Show</button>
          <a href={`/api/payroll/summary.csv?from=${from}&to=${to}`} className="inline-flex items-center gap-1.5 px-3 py-2 border border-slate-300 rounded-lg font-semibold text-slate-700 hover:bg-slate-100">
            <Download className="w-3.5 h-3.5" /> Download
          </a>
        </div>
      </div>

      {loading ? (
        <LoadingState message="Working out technician pay..." />
      ) : error ? (
        <ErrorState title="Could not load technician pay" message={error} onRetry={load} />
      ) : (
        <>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
            <div className="bg-white border border-slate-200 rounded-xl p-4">
              <div className="text-xs text-slate-500">Owed for this period</div>
              <div className="text-2xl font-extrabold text-slate-900">{rupees(summary.total_due)}</div>
            </div>
            <div className="bg-white border border-slate-200 rounded-xl p-4">
              <div className="text-xs text-slate-500">Unpaid hours</div>
              <div className="text-2xl font-extrabold text-slate-900">{summary.total_hours}</div>
            </div>
          </div>
          <DataTable columns={columns} data={summary.rows} searchPlaceholder="Search technicians..." emptyTitle="No finished jobs in this period" emptyDescription="Pick a wider period to see more." />
        </>
      )}

      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h4 className="text-base font-bold text-slate-900">Payments made</h4>
          <a href="/api/payroll/payouts.csv" className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-700 hover:underline">
            <Download className="w-3.5 h-3.5" /> Download
          </a>
        </div>
        <DataTable columns={payoutColumns} data={payouts} searchPlaceholder="Search payments..." emptyTitle="No payments recorded yet" emptyDescription="Payments you record to technicians appear here." />
      </div>

      <Modal isOpen={Boolean(paying)} onClose={() => setPaying(null)} title={paying ? `Pay ${paying.technician_name}` : 'Pay'} maxWidth="max-w-md">
        {paying && (
          <div className="space-y-4 text-sm">
            <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 text-xs space-y-1">
              <div>{paying.unpaid_jobs} finished job{paying.unpaid_jobs === 1 ? '' : 's'}, {paying.unpaid_hours} hours</div>
              <div>at ₹{paying.hourly_rate} an hour</div>
              <div className="text-base font-extrabold text-slate-900">{rupees(paying.amount_due)}</div>
              <div className="text-slate-500">Jobs finished {from} to {to}</div>
            </div>
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Bank transfer or voucher reference (optional)</label>
              <input value={reference} maxLength={100} onChange={(e) => setReference(e.target.value)} className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:outline-none" />
            </div>
            <p className="text-[11px] text-slate-500">Once recorded, these jobs are marked as paid and cannot be paid again.</p>
            {payError && <div className="text-xs text-rose-700 bg-rose-50 border border-rose-200 rounded-lg p-2.5">{payError}</div>}
            <div className="flex justify-end gap-3 pt-2 border-t border-slate-200">
              <button onClick={() => setPaying(null)} className="px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-100 text-xs">Cancel</button>
              <button onClick={confirmPay} disabled={busy} className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold rounded-lg text-xs disabled:opacity-50">
                {busy ? 'Recording...' : 'Record payment'}
              </button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
