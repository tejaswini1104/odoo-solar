import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import DataTable from '../components/DataTable';
import StatusBadge from '../components/StatusBadge';
import Modal from '../components/Modal';
import { LoadingState, ErrorState } from '../components/States';
import { useToast } from '../components/Toast';
import { MapPin, Phone } from 'lucide-react';

const WAITING_FOR_VERDICT = 'Assigned';

export default function RepairVisits() {
  const [visits, setVisits] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [target, setTarget] = useState(null);
  const [form, setForm] = useState({ needs_replacement: false, notes: '' });
  const [submitting, setSubmitting] = useState(false);
  const { addToast } = useToast();

  const load = async () => {
    try {
      setLoading(true);
      setError(null);
      setVisits(await api.getMyRepairVisits());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const openReport = (visit) => {
    setForm({ needs_replacement: false, notes: '' });
    setTarget(visit);
  };

  const submitReport = async (e) => {
    e.preventDefault();
    try {
      setSubmitting(true);
      await api.reportRepairVisit(target.id, form.needs_replacement, form.notes.trim());
      addToast(`Report sent to Customer Support for ${target.reference}.`, 'success');
      setTarget(null);
      load();
    } catch (err) {
      addToast(`Error: ${err.message}`, 'error', 6000);
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <LoadingState message="Loading your repair visits..." />;
  if (error) return <ErrorState title="Could not load repair visits" message={error} onRetry={load} />;

  const columns = [
    {
      header: 'Ticket & Fault',
      accessor: 'reference',
      render: (row) => (
        <div className="text-xs">
          <span className="font-mono font-bold text-slate-800">{row.reference}</span>
          <div className="font-semibold text-slate-900 mt-0.5">{row.title}</div>
          <div className="text-slate-500 max-w-xs">{row.description}</div>
          <div className="mt-1"><StatusBadge status={row.priority} /></div>
        </div>
      )
    },
    {
      header: 'Customer & Site',
      accessor: 'customer_name',
      render: (row) => (
        <div className="text-xs space-y-0.5">
          <div className="font-semibold text-slate-900">{row.customer_name}</div>
          <div className="flex items-center gap-1 text-slate-600"><Phone className="w-3 h-3" /> {row.customer_phone}</div>
          <div className="flex items-center gap-1 text-slate-600"><MapPin className="w-3 h-3" /> {row.customer_address}</div>
          <span className="font-mono text-[11px] font-bold text-purple-700">{row.equipment_serial}</span>
        </div>
      )
    },
    {
      header: 'Status',
      accessor: 'status',
      render: (row) => (
        <div className="text-xs space-y-1">
          <StatusBadge status={row.status} />
          <div><StatusBadge status={row.service_type} /></div>
          {row.status === 'Quotation Sent' && <div className="text-slate-500">Waiting for the customer to approve the quotation</div>}
          {row.status === 'Awaiting Dispatch' && <div className="text-slate-500">Waiting for the warehouse to dispatch the replacement</div>}
          {row.status === 'In Progress' && <div className="text-slate-500">Repair on site, then tell Support it is done</div>}
          {row.status === 'Dispatched' && <div className="text-slate-500">Replacement dispatched{row.dispatch_serial ? `: ${row.dispatch_serial}` : ''}. Fit it at the site.</div>}
        </div>
      )
    },
    {
      header: 'Your report',
      accessor: 'id',
      render: (row) =>
        row.status === WAITING_FOR_VERDICT ? (
          <button
            onClick={() => openReport(row)}
            className="px-2.5 py-1 text-xs font-semibold rounded bg-amber-500 hover:bg-amber-600 text-slate-950 transition"
          >
            Report finding
          </button>
        ) : row.needs_replacement !== null ? (
          <div className="text-xs">
            <div className={`font-semibold ${row.needs_replacement ? 'text-purple-700' : 'text-emerald-700'}`}>
              {row.needs_replacement ? 'Needs replacement' : 'Repairable on site'}
            </div>
            {row.inspection_notes && <div className="text-slate-500 max-w-xs">{row.inspection_notes}</div>}
          </div>
        ) : (
          <span className="text-xs text-slate-400">-</span>
        )
    }
  ];

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-lg font-bold text-slate-900">My Repair Visits</h3>
        <p className="text-xs text-slate-500">
          Tickets are assigned to you automatically. Visit the customer, then report whether the unit can be repaired on site or needs a replacement.
          Customer Support is told straight away and takes it from there.
        </p>
      </div>

      <DataTable
        columns={columns}
        data={visits}
        searchPlaceholder="Search by ticket, customer or serial..."
        emptyTitle="No repair visits"
        emptyDescription="Tickets assigned to you will appear here."
      />

      <Modal isOpen={!!target} onClose={() => setTarget(null)} title="Report your finding">
        {target && (
          <form onSubmit={submitReport} className="space-y-4 text-sm">
            <p className="text-xs text-slate-500">{target.reference} · {target.customer_name} · {target.equipment_serial}</p>
            <div className="grid grid-cols-2 gap-2">
              <button
                type="button"
                onClick={() => setForm({ ...form, needs_replacement: false })}
                className={`px-3 py-2 rounded-lg border text-xs font-semibold ${!form.needs_replacement ? 'border-emerald-500 bg-emerald-50 text-emerald-800' : 'border-slate-300 text-slate-700'}`}
              >
                Can be repaired on site
              </button>
              <button
                type="button"
                onClick={() => setForm({ ...form, needs_replacement: true })}
                className={`px-3 py-2 rounded-lg border text-xs font-semibold ${form.needs_replacement ? 'border-purple-500 bg-purple-50 text-purple-800' : 'border-slate-300 text-slate-700'}`}
              >
                Needs a replacement
              </button>
            </div>
            <textarea
              maxLength={2000}
              rows={3}
              value={form.notes}
              onChange={(e) => setForm({ ...form, notes: e.target.value })}
              placeholder="What you found at the site"
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:outline-none"
            />
            {target.service_type === 'BILLABLE' && (
              <p className="text-xs text-rose-700">Out of warranty: the customer will be sent a quotation to approve.</p>
            )}
            <div className="flex justify-end gap-3 pt-3 border-t border-slate-200">
              <button type="button" onClick={() => setTarget(null)} className="px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-100 transition">
                Cancel
              </button>
              <button type="submit" disabled={submitting} className="px-4 py-2 bg-amber-500 hover:bg-amber-600 text-slate-950 font-semibold rounded-lg transition disabled:opacity-50">
                Send report to Support
              </button>
            </div>
          </form>
        )}
      </Modal>
    </div>
  );
}
