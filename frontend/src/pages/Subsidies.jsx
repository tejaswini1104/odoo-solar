import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import { useAuth } from '../auth/AuthContext';
import DataTable from '../components/DataTable';
import Modal from '../components/Modal';
import { LoadingState, ErrorState } from '../components/States';
import { useToast } from '../components/Toast';

const FLOW = ['Documents pending', 'Documents collected', 'Applied', 'Approved', 'Disbursed'];
const rupees = (n) => (n == null ? '-' : `₹${Number(n).toLocaleString('en-IN')}`);
const showDate = (v) => (v ? new Date(v).toLocaleDateString('en-IN') : null);

const badge = (status) => {
  if (status === 'Disbursed') return 'bg-emerald-50 text-emerald-700 border-emerald-200';
  if (status === 'Rejected') return 'bg-rose-50 text-rose-700 border-rose-200';
  if (status === 'Approved') return 'bg-teal-50 text-teal-700 border-teal-200';
  if (status === 'Applied') return 'bg-blue-50 text-blue-700 border-blue-200';
  return 'bg-amber-50 text-amber-700 border-amber-200';
};

// The government rooftop subsidy file for each order: from collecting documents to the money arriving.
export default function Subsidies() {
  const { user } = useAuth();
  const canWork = user?.role === 'sales';
  const { addToast } = useToast();
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [active, setActive] = useState(null);
  const [form, setForm] = useState({ reference_number: '', expected_amount: '', received_amount: '', note: '' });
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState(null);

  const load = async () => {
    try {
      setLoading(true);
      setError(null);
      setFiles(await api.getSubsidies());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const openFile = (file) => {
    setActive(file);
    setFormError(null);
    setForm({
      reference_number: file.reference_number || '',
      expected_amount: file.expected_amount ?? '',
      received_amount: file.received_amount ?? '',
      note: '',
    });
  };

  const nextStep = (file) => {
    const index = FLOW.indexOf(file.status);
    return index >= 0 && index + 1 < FLOW.length ? FLOW[index + 1] : null;
  };

  const save = async (status) => {
    setFormError(null);
    try {
      setSaving(true);
      const body = { note: form.note || null };
      if (status) body.status = status;
      if (form.reference_number.trim()) body.reference_number = form.reference_number.trim();
      if (form.expected_amount !== '') body.expected_amount = Number(form.expected_amount);
      if (form.received_amount !== '') body.received_amount = Number(form.received_amount);
      const updated = await api.updateSubsidy(active.id, body);
      addToast(status ? `Subsidy file moved to ${status}.` : 'Subsidy file updated.', 'success');
      setActive(updated);
      setForm({ reference_number: updated.reference_number || '', expected_amount: updated.expected_amount ?? '', received_amount: updated.received_amount ?? '', note: '' });
      load();
    } catch (err) {
      setFormError(err.message);
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <LoadingState message="Loading subsidy files..." />;
  if (error) return <ErrorState title="Could not load subsidy files" message={error} onRetry={load} />;

  const columns = [
    {
      header: 'Customer and order',
      accessor: 'customer_name',
      render: (row) => (
        <div className="text-xs">
          <div className="font-semibold text-slate-900">{row.customer_name}</div>
          <div className="text-slate-500 font-mono">SO-{String(row.order_id).padStart(4, '0')} · {row.package_name}</div>
        </div>
      )
    },
    {
      header: 'Status',
      accessor: 'status',
      render: (row) => <span className={`inline-flex px-2.5 py-0.5 rounded-full text-xs font-medium border ${badge(row.status)}`}>{row.status}</span>
    },
    {
      header: 'Application number',
      accessor: 'reference_number',
      render: (row) => <span className="font-mono text-xs">{row.reference_number || '-'}</span>
    },
    {
      header: 'Subsidy amount',
      accessor: 'expected_amount',
      render: (row) => (
        <div className="text-xs">
          <div>Approved: <strong>{rupees(row.expected_amount)}</strong></div>
          <div className="text-slate-500">Received: {rupees(row.received_amount)}</div>
        </div>
      )
    },
    {
      header: 'Action',
      accessor: 'id',
      render: (row) => (
        <button onClick={() => openFile(row)} className="px-2.5 py-1 text-xs font-semibold rounded border border-slate-300 hover:bg-slate-100 text-slate-700 transition">
          {canWork ? 'Open file' : 'View file'}
        </button>
      )
    },
  ];

  const finished = active && (active.status === 'Disbursed' || active.status === 'Rejected');
  const next = active ? nextStep(active) : null;
  const field = 'w-full px-3 py-2 border border-slate-300 rounded-lg bg-white focus:ring-2 focus:ring-amber-500 focus:outline-none';
  const label = 'block text-xs font-semibold text-slate-700 mb-1';

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-lg font-bold text-slate-900">Subsidy files</h3>
        <p className="text-xs text-slate-500">
          A file opens automatically when an order is confirmed for a customer who asked for the government subsidy. Each file moves one step at a time and keeps its history.
        </p>
      </div>

      <DataTable columns={columns} data={files} searchPlaceholder="Search by customer or application number..." emptyTitle="No subsidy files yet" emptyDescription="Files appear when an order is confirmed for a customer who asked for the subsidy." />

      <Modal isOpen={Boolean(active)} onClose={() => setActive(null)} title={active ? `Subsidy file for ${active.customer_name}` : 'Subsidy file'} maxWidth="max-w-2xl">
        {active && (
          <div className="space-y-4 text-sm">
            <ol className="flex flex-wrap gap-x-4 gap-y-1 text-xs">
              {FLOW.map((step) => {
                const reached = FLOW.indexOf(active.status) >= FLOW.indexOf(step);
                return <li key={step} className={reached && active.status !== 'Rejected' ? 'text-emerald-700 font-semibold' : 'text-slate-400'}>{reached && active.status !== 'Rejected' ? '✓' : '○'} {step}</li>;
              })}
              {active.status === 'Rejected' && <li className="text-rose-700 font-semibold">✗ Rejected</li>}
            </ol>

            <div>
              <h4 className="text-xs font-bold text-slate-900 mb-1.5">History</h4>
              <ul className="space-y-1 max-h-36 overflow-y-auto text-xs border border-slate-200 rounded-lg p-2 bg-slate-50">
                {active.events.map((event, idx) => (
                  <li key={idx}>
                    <span className="font-semibold text-slate-800">{event.status}</span>
                    <span className="text-slate-400"> · {new Date(`${event.at}Z`).toLocaleString('en-IN')}</span>
                    {event.note && <div className="text-slate-600">{event.note}</div>}
                  </li>
                ))}
              </ul>
            </div>

            {canWork ? (
              <div className="space-y-3">
                {!finished && (
                  <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                    <div>
                      <label className={label}>Application number</label>
                      <input maxLength={100} value={form.reference_number} onChange={(e) => setForm({ ...form, reference_number: e.target.value })} className={field} />
                    </div>
                    <div>
                      <label className={label}>Approved amount (₹)</label>
                      <input max="10000000" type="number" min="0" value={form.expected_amount} onChange={(e) => setForm({ ...form, expected_amount: e.target.value })} className={field} />
                    </div>
                    <div>
                      <label className={label}>Amount received (₹)</label>
                      <input max="10000000" type="number" min="0" value={form.received_amount} onChange={(e) => setForm({ ...form, received_amount: e.target.value })} className={field} />
                    </div>
                  </div>
                )}
                <div>
                  <label className={label}>Note</label>
                  <textarea rows={2} maxLength={1000} value={form.note} onChange={(e) => setForm({ ...form, note: e.target.value })} className={field} placeholder="Optional, saved in the history" />
                </div>
                {formError && <div className="text-xs text-rose-700 bg-rose-50 border border-rose-200 rounded-lg p-2.5">{formError}</div>}
                <div className="flex flex-wrap justify-end gap-2 pt-2 border-t border-slate-200">
                  <button type="button" disabled={saving || (!form.note && finished)} onClick={() => save(null)} className="px-3 py-2 text-xs font-semibold rounded-lg border border-slate-300 text-slate-700 hover:bg-slate-100 disabled:opacity-40">
                    {finished ? 'Add note' : 'Save details'}
                  </button>
                  {!finished && (
                    <button type="button" disabled={saving} onClick={() => save('Rejected')} className="px-3 py-2 text-xs font-semibold rounded-lg border border-rose-300 text-rose-700 hover:bg-rose-50 disabled:opacity-40">
                      Mark rejected
                    </button>
                  )}
                  {next && (
                    <button type="button" disabled={saving} onClick={() => save(next)} className="px-3 py-2 text-xs font-semibold rounded-lg bg-amber-500 hover:bg-amber-600 text-slate-950 disabled:opacity-40">
                      Move to: {next}
                    </button>
                  )}
                </div>
              </div>
            ) : (
              <dl className="grid grid-cols-2 gap-x-6 gap-y-1 text-xs bg-slate-50 border border-slate-200 rounded-lg p-3">
                <dt className="text-slate-500">Application number</dt><dd className="font-mono">{active.reference_number || '-'}</dd>
                <dt className="text-slate-500">Approved</dt><dd>{rupees(active.expected_amount)} {active.approved_on ? `on ${showDate(active.approved_on)}` : ''}</dd>
                <dt className="text-slate-500">Received</dt><dd>{rupees(active.received_amount)} {active.disbursed_on ? `on ${showDate(active.disbursed_on)}` : ''}</dd>
              </dl>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
}
