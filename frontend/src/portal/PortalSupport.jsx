import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import DataTable from '../components/DataTable';
import StatusBadge from '../components/StatusBadge';
import { LoadingState, ErrorState } from '../components/States';
import { useToast } from '../components/Toast';

const rupees = (n) => `₹${Number(n || 0).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
// A serial-numbered unit is picked by its serial; the panels by their warranty id
const optionValue = (w) => (w.serial_number ? w.serial_number : `w:${w.id}`);
const EMPTY_FORM = { equipment_serial: '', title: '', description: '', priority: 'Medium' };

export default function PortalSupport() {
  const [tickets, setTickets] = useState([]);
  const [serials, setSerials] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const { addToast } = useToast();

  const load = async () => {
    try {
      setLoading(true);
      setError(null);
      const [ticketData, warrantyData] = await Promise.all([api.getMyTickets(), api.getMyWarranties()]);
      setTickets(ticketData);
      // Serial-numbered units, and the panels' bulk warranty (they have no serial numbers). Swapped-out units are left out.
      setSerials(warrantyData.filter((w) => (w.serial_number || w.warranty_type === 'bulk') && w.status !== 'Replaced'));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      setSubmitting(true);
      const choice = form.equipment_serial || optionValue(serials[0]);
      const { equipment_serial, ...rest } = form;
      const created = await api.raiseTicket(
        choice.startsWith('w:')
          ? { ...rest, warranty_id: Number(choice.slice(2)) }
          : { ...rest, equipment_serial: choice }
      );
      if (created.service_type === 'COVERED') {
        addToast(`Ticket ${created.reference} raised. Your equipment is under warranty, so there is no charge.`, 'success', 7000);
      } else {
        addToast(`Ticket ${created.reference} raised. The warranty has ended, so this repair is chargeable. A technician will visit first, then you will receive a quotation to approve.`, 'info', 8000);
      }
      setForm(EMPTY_FORM);
      load();
    } catch (err) {
      addToast(`Could not raise ticket: ${err.message}`, 'error', 6000);
    } finally {
      setSubmitting(false);
    }
  };

  const handleConfirm = async (ticket) => {
    try {
      await api.confirmMyTicket(ticket.id);
      addToast(`Thank you. Ticket ${ticket.reference} is confirmed as fixed.`, 'success');
      load();
    } catch (err) {
      addToast(`Could not confirm: ${err.message}`, 'error');
    }
  };

  const handleQuote = async (ticket, approved) => {
    try {
      await api.decideMyTicketQuote(ticket.id, approved);
      addToast(
        approved ? `Thank you. We will go ahead with ticket ${ticket.reference}.` : `Quotation declined. Ticket ${ticket.reference} is closed and you will not be charged.`,
        approved ? 'success' : 'info', 6000
      );
      load();
    } catch (err) {
      addToast(`Could not record your answer: ${err.message}`, 'error');
    }
  };

  if (loading) return <LoadingState message="Loading your tickets..." />;
  if (error) return <ErrorState title="Could not load tickets" message={error} onRetry={load} />;

  const columns = [
    {
      header: 'Ticket',
      accessor: 'reference',
      render: (row) => (
        <div className="text-xs">
          <span className="font-mono font-bold text-slate-800">{row.reference}</span>
          <div className="font-semibold text-slate-900 mt-0.5">{row.title}</div>
          <div className="text-slate-500 truncate max-w-xs">{row.description}</div>
        </div>
      )
    },
    {
      header: 'Equipment',
      accessor: 'equipment_serial',
      render: (row) => <span className="font-mono text-xs font-bold text-purple-700">{row.equipment_serial}</span>
    },
    {
      header: 'Warranty decision',
      accessor: 'service_type',
      render: (row) => (
        <div className="text-xs space-y-1">
          <StatusBadge status={row.service_type} />
          <div className={row.service_type === 'COVERED' ? 'text-emerald-700 font-semibold' : 'text-rose-700 font-semibold'}>
            {row.service_type === 'COVERED' ? 'No charge' : `Charge: ${rupees(row.customer_charge)}`}
          </div>
          {row.service_type === 'BILLABLE' && (
            <Link to="/portal/invoices" className="text-blue-600 hover:underline font-semibold">View invoices</Link>
          )}
        </div>
      )
    },
    {
      header: 'Status',
      accessor: 'status',
      render: (row) => (
        <div className="text-xs space-y-1">
          <StatusBadge status={row.status} />
          {row.technician_name && <div className="text-slate-500">Technician: {row.technician_name}</div>}
          {row.status === 'Dispatched' && <div className="text-slate-500">Replacement on its way</div>}
        </div>
      )
    },
    {
      header: 'Action',
      accessor: 'id',
      render: (row) =>
        row.status === 'Quotation Sent' && row.quote_status === 'Pending' ? (
          <div className="text-xs space-y-1.5 max-w-[16rem]">
            {row.quote_lines.map((l, i) => (
              <div key={i} className="flex justify-between gap-3 text-slate-600"><span>{l.description}</span><span>{rupees(l.total)}</span></div>
            ))}
            <div className="font-bold text-slate-900">Total with GST: {rupees(row.customer_charge)}</div>
            <div className="flex gap-1.5">
              <button onClick={() => handleQuote(row, true)} className="px-2.5 py-1 font-semibold rounded bg-emerald-600 hover:bg-emerald-700 text-white transition">
                Approve
              </button>
              <button onClick={() => handleQuote(row, false)} className="px-2.5 py-1 font-semibold rounded border border-rose-300 text-rose-700 hover:bg-rose-50 transition">
                Reject
              </button>
            </div>
          </div>
        ) : row.status === 'Resolved' && !row.customer_confirmed ? (
          <button
            onClick={() => handleConfirm(row)}
            className="px-2.5 py-1 text-xs font-semibold rounded bg-emerald-600 hover:bg-emerald-700 text-white transition"
          >
            Confirm it works
          </button>
        ) : (
          <span className="text-xs text-slate-400">-</span>
        )
    },
  ];

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-xl border border-slate-200 p-5">
        <h2 className="text-lg font-bold text-slate-900">Raise a support ticket</h2>
        <p className="text-xs text-slate-500 mb-4">
          We check your warranty automatically. Equipment under warranty is repaired free of charge.
        </p>

        {serials.length === 0 ? (
          <p className="text-xs text-slate-500">
            You can raise a ticket once your installation is complete and your equipment is registered.
          </p>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4 text-sm max-w-xl">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Equipment</label>
              <select
                value={form.equipment_serial || optionValue(serials[0])}
                onChange={(e) => setForm({ ...form, equipment_serial: e.target.value })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg bg-white font-mono text-xs focus:ring-2 focus:ring-amber-500 focus:outline-none"
              >
                {serials.map((w) => (
                  <option key={w.id} value={optionValue(w)}>
                    {w.serial_number || 'Solar panels'} · {w.product_name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">What is wrong?</label>
              <input maxLength={255}
                required
                minLength={3}
                type="text"
                value={form.title}
                onChange={(e) => setForm({ ...form, title: e.target.value })}
                placeholder="For example: inverter shows a fault code, no power"
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Details</label>
              <textarea maxLength={2000}
                required
                minLength={5}
                rows={3}
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
                placeholder="Fault code, when it started, anything you noticed"
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Priority</label>
              <select
                value={form.priority}
                onChange={(e) => setForm({ ...form, priority: e.target.value })}
                className="px-3 py-2 border border-slate-300 rounded-lg bg-white focus:ring-2 focus:ring-amber-500 focus:outline-none"
              >
                <option value="Low">Low</option>
                <option value="Medium">Medium</option>
                <option value="High">High</option>
                <option value="Urgent">Urgent (no power at all)</option>
              </select>
            </div>

            <button
              type="submit"
              disabled={submitting}
              className="px-4 py-2 bg-amber-500 hover:bg-amber-600 text-slate-950 font-semibold rounded-lg transition disabled:opacity-50"
            >
              {submitting ? 'Checking your warranty...' : 'Raise ticket'}
            </button>
          </form>
        )}
      </div>

      <div className="space-y-3">
        <h3 className="text-lg font-bold text-slate-900">My tickets</h3>
        <DataTable
          columns={columns}
          data={tickets}
          searchPlaceholder="Search your tickets..."
          emptyTitle="No tickets yet"
          emptyDescription="Tickets you raise will appear here."
        />
      </div>
    </div>
  );
}
