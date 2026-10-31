import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import DataTable from '../components/DataTable';
import StatusBadge from '../components/StatusBadge';
import Modal from '../components/Modal';
import { LoadingState, ErrorState } from '../components/States';
import { useToast } from '../components/Toast';
import {
  LifeBuoy,
  Plus,
  CheckCircle,
  FileText,
  AlertCircle,
  CheckCheck,
  UserCheck,
  ShieldCheck,
  Receipt
} from 'lucide-react';

export default function ServiceTickets({ setActiveTab }) {
  const [tickets, setTickets] = useState([]);
  const [customers, setCustomers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const { addToast } = useToast();

  const [formData, setFormData] = useState({
    customer_id: '',
    equipment_serial: 'INV-2026-0042',
    title: '',
    description: '',
    priority: 'Medium'
  });

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [ticketData, custData] = await Promise.all([
        api.getTickets(),
        api.getCustomers()
      ]);
      setTickets(ticketData);
      setCustomers(custData);
      if (custData.length > 0 && !formData.customer_id) {
        setFormData((prev) => ({ ...prev, customer_id: custData[0].id }));
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleCreate = async (e) => {
    e.preventDefault();
    try {
      setSubmitting(true);
      const created = await api.createTicket({
        ...formData,
        customer_id: parseInt(formData.customer_id)
      });

      if (created.service_type === 'COVERED') {
        addToast(
          `Ticket #${created.id} Created! Serial '${created.equipment_serial}' has ACTIVE warranty → Service Type: COVERED (₹0 charge).`,
          'success',
          7000
        );
      } else {
        addToast(
          `Ticket #${created.id} Created! Serial '${created.equipment_serial}' is EXPIRED/UNCOVERED → Service Type: BILLABLE (Draft invoice #${created.invoice_id} created).`,
          'info',
          7000
        );
      }

      setIsModalOpen(false);
      loadData();
    } catch (err) {
      addToast(`Ticket creation failed: ${err.message}`, 'error');
    } finally {
      setSubmitting(false);
    }
  };

  const handleResolve = async (id) => {
    try {
      await api.resolveTicket(id);
      addToast(`Ticket #${id} marked as Resolved!`, 'success');
      loadData();
    } catch (err) {
      addToast(`Error: ${err.message}`, 'error');
    }
  };

  const handleCustomerConfirm = async (id) => {
    try {
      await api.customerConfirmTicket(id);
      addToast(`Customer satisfaction confirmed for Ticket #${id}! Ready to close.`, 'success');
      loadData();
    } catch (err) {
      addToast(`Error: ${err.message}`, 'error');
    }
  };

  const handleClose = async (id) => {
    try {
      await api.closeTicket(id);
      addToast(`Ticket #${id} has been CLOSED.`, 'success');
      loadData();
    } catch (err) {
      // Hard gate rejects if customer_confirmed is false!
      addToast(`Closure Blocked: ${err.message}`, 'error', 6000);
    }
  };

  const columns = [
    {
      header: 'Ticket ID & Title',
      accessor: 'id',
      render: (row) => (
        <div>
          <span className="font-mono text-xs font-bold text-slate-800">TCK-{row.id.toString().padStart(4, '0')}</span>
          <div className="font-semibold text-slate-900 mt-0.5">{row.title}</div>
          <div className="text-[11px] text-slate-500 truncate max-w-xs">{row.description}</div>
        </div>
      )
    },
    {
      header: 'Customer & Serial No.',
      accessor: 'customer_name',
      render: (row) => (
        <div className="text-xs">
          <div className="font-medium text-slate-800">{row.customer_name}</div>
          <span className="font-mono text-[11px] font-bold text-purple-700 bg-purple-50 px-1.5 py-0.5 rounded border border-purple-200 mt-0.5 inline-block">
            {row.equipment_serial}
          </span>
        </div>
      )
    },
    {
      header: 'Warranty Decision',
      accessor: 'service_type',
      render: (row) => (
        <div className="text-xs space-y-1">
          <StatusBadge status={row.service_type} />
          <div>
            {row.service_type === 'COVERED' ? (
              <span className="text-emerald-700 font-bold block">Charge: ₹0 (Free)</span>
            ) : (
              <div className="space-y-0.5">
                <span className="text-rose-700 font-bold block">Billable: ₹{row.customer_charge?.toLocaleString()}</span>
                {row.invoice_id && (
                  <button
                    onClick={() => setActiveTab && setActiveTab('invoices')}
                    className="text-[11px] text-blue-600 hover:underline flex items-center gap-1 font-semibold"
                  >
                    <Receipt className="w-3 h-3" /> View Draft Invoice
                  </button>
                )}
              </div>
            )}
          </div>
        </div>
      )
    },
    {
      header: 'Status & Confirmation',
      accessor: 'status',
      render: (row) => (
        <div className="text-xs space-y-1">
          <StatusBadge status={row.status} />
          <div>
            {row.customer_confirmed ? (
              <span className="text-teal-700 font-semibold text-[11px] flex items-center gap-1">
                <CheckCheck className="w-3.5 h-3.5 text-teal-600" /> Customer Confirmed
              </span>
            ) : (
              <span className="text-amber-600 font-medium text-[11px] flex items-center gap-1">
                <AlertCircle className="w-3.5 h-3.5" /> Awaiting Confirmation
              </span>
            )}
          </div>
        </div>
      )
    },
    {
      header: 'Workflow Actions',
      accessor: 'id',
      render: (row) => (
        <div className="flex flex-wrap items-center gap-1.5">
          {row.status === 'Open' || row.status === 'In Progress' || row.status === 'Assigned' ? (
            <button
              onClick={() => handleResolve(row.id)}
              className="px-2.5 py-1 text-xs font-semibold rounded bg-amber-500 hover:bg-amber-600 text-slate-950 transition"
              title="Mark ticket resolved"
            >
              Resolve
            </button>
          ) : null}

          {!row.customer_confirmed && row.status !== 'Closed' ? (
            <button
              onClick={() => handleCustomerConfirm(row.id)}
              className="px-2.5 py-1 text-xs font-semibold rounded border border-teal-300 text-teal-800 hover:bg-teal-50 transition"
              title="Customer confirmed resolution"
            >
              Confirm
            </button>
          ) : null}

          {row.status !== 'Closed' ? (
            <button
              onClick={() => handleClose(row.id)}
              className={`px-2.5 py-1 text-xs font-semibold rounded transition ${
                row.customer_confirmed
                  ? 'bg-slate-800 hover:bg-slate-900 text-white'
                  : 'bg-slate-100 text-slate-400 hover:bg-slate-200'
              }`}
              title={row.customer_confirmed ? 'Close ticket' : 'Requires Customer Confirmation first'}
            >
              Close
            </button>
          ) : (
            <span className="text-xs text-slate-400 font-semibold">Closed</span>
          )}
        </div>
      )
    }
  ];

  if (loading) return <LoadingState message="Loading service tickets..." />;
  if (error) return <ErrorState title="Failed to load tickets" message={error} onRetry={loadData} />;

  return (
    <div className="space-y-4">
      {/* Policy banner */}
      <div className="bg-amber-50 border border-amber-200 rounded-xl p-3.5 text-xs text-amber-950 flex items-start gap-3">
        <ShieldCheck className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
        <div>
          <strong>AUTOMATED WARRANTY LOOKUP & COVERED/BILLABLE DECISION:</strong> When a service ticket is created
          with an equipment serial number, the system automatically checks its active warranty. If warranty is Active,
          the visit is <strong>COVERED (₹0)</strong>. If Expired, it is <strong>BILLABLE</strong> and automatically
          spawns an editable draft invoice. <em>Tickets cannot be Closed without prior customer confirmation!</em>
        </div>
      </div>

      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
        <div>
          <h3 className="text-lg font-bold text-slate-900">After-Sales Service Tickets</h3>
          <p className="text-xs text-slate-500">Track equipment complaints, evaluate warranty coverage, and bill out-of-warranty repairs.</p>
        </div>
        <button
          onClick={() => setIsModalOpen(true)}
          className="inline-flex items-center gap-2 px-3.5 py-2 bg-amber-500 hover:bg-amber-600 text-slate-950 rounded-lg text-sm font-semibold shadow-xs transition"
        >
          <Plus className="w-4 h-4" /> Create Service Ticket
        </button>
      </div>

      <DataTable
        columns={columns}
        data={tickets}
        searchPlaceholder="Search tickets by title, customer, or serial..."
      />

      {/* Create Ticket Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title="Open Service Ticket (With Auto Warranty Lookup)"
      >
        <form onSubmit={handleCreate} className="space-y-4 text-sm">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Customer *</label>
            <select
              required
              value={formData.customer_id}
              onChange={(e) => setFormData({ ...formData, customer_id: e.target.value })}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:outline-none bg-white"
            >
              {customers.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name} ({c.city})
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">
              Equipment Serial Number *
            </label>
            <input
              required
              type="text"
              value={formData.equipment_serial}
              onChange={(e) => setFormData({ ...formData, equipment_serial: e.target.value })}
              placeholder="e.g. INV-2026-0042 (Active) or INV-2023-0018 (Expired)"
              className="w-full px-3 py-2 border border-slate-300 rounded-lg font-mono text-sm focus:ring-2 focus:ring-amber-500 focus:outline-none"
            />
            <div className="flex gap-2 mt-1.5">
              <button
                type="button"
                onClick={() => setFormData({ ...formData, equipment_serial: 'INV-2026-0042', title: 'Inverter stopped working' })}
                className="text-[11px] text-emerald-700 bg-emerald-50 hover:bg-emerald-100 px-2 py-0.5 rounded border border-emerald-200 font-mono"
              >
                Use Seed: INV-2026-0042 (COVERED ₹0)
              </button>
              <button
                type="button"
                onClick={() => setFormData({ ...formData, equipment_serial: 'INV-2023-0018', title: 'Inverter hardware fault E04' })}
                className="text-[11px] text-rose-700 bg-rose-50 hover:bg-rose-100 px-2 py-0.5 rounded border border-rose-200 font-mono"
              >
                Use Seed: INV-2023-0018 (BILLABLE)
              </button>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Ticket Title / Fault Summary *</label>
            <input
              required
              type="text"
              value={formData.title}
              onChange={(e) => setFormData({ ...formData, title: e.target.value })}
              placeholder="e.g. Inverter display blackout, no power output"
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:outline-none"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Priority</label>
              <select
                value={formData.priority}
                onChange={(e) => setFormData({ ...formData, priority: e.target.value })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:outline-none bg-white"
              >
                <option value="Low">Low</option>
                <option value="Medium">Medium</option>
                <option value="High">High</option>
                <option value="Urgent">Urgent (Zero Generation)</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Detailed Description *</label>
            <textarea
              required
              rows={2}
              value={formData.description}
              onChange={(e) => setFormData({ ...formData, description: e.target.value })}
              placeholder="Customer's report, error codes on display, technician pre-notes..."
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:outline-none"
            />
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t border-slate-200">
            <button
              type="button"
              onClick={() => setIsModalOpen(false)}
              className="px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-100 transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="px-4 py-2 bg-amber-500 hover:bg-amber-600 text-slate-950 font-semibold rounded-lg transition disabled:opacity-50"
            >
              {submitting ? 'Checking Warranty...' : 'Submit Ticket & Check Warranty'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
