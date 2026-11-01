import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import DataTable from '../components/DataTable';
import StatusBadge from '../components/StatusBadge';
import Modal from '../components/Modal';
import { LoadingState, ErrorState } from '../components/States';
import { useToast } from '../components/Toast';
import CameraScanner from '../components/CameraScanner';
import { cameraScanSupported } from '../utils/cameraSupport';
import { serialFromScan } from '../utils/scanText';
import {
  LifeBuoy,
  Camera,
  Plus,
  CheckCircle,
  FileText,
  AlertCircle,
  CheckCheck,
  UserCheck,
  ShieldCheck,
  Receipt
} from 'lucide-react';
import { useAuth } from '../auth/AuthContext';

export default function ServiceTickets({ setActiveTab }) {
  const { user } = useAuth();
  const canManage = user?.role === 'support'; // Support raises, resolves and closes tickets; other roles view them
  const [tickets, setTickets] = useState([]);
  const [customers, setCustomers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  // Support find the customer by phone, name, address or the serial on the unit, then pick the faulty equipment
  const [query, setQuery] = useState('');
  const [matches, setMatches] = useState(null);
  const [picked, setPicked] = useState(null);
  const [scanning, setScanning] = useState(false);

  useEffect(() => {
    const term = query.trim();
    if (term.length < 2) { setMatches(null); return undefined; }
    const timer = setTimeout(() => {
      api.searchCustomers(term).then(setMatches).catch(() => setMatches([]));
    }, 300);
    return () => clearTimeout(timer);
  }, [query]);

  const chooseEquipment = (customer, item) => {
    setPicked({ customer, item });
    // The panels have no serial numbers, so a claim on them is made through their bulk warranty
    setFormData((prev) => ({ ...prev, customer_id: customer.id, equipment_serial: item.serial_number || '', warranty_id: item.warranty_id ?? null }));
  };
  const { addToast } = useToast();

  const [formData, setFormData] = useState({
    customer_id: '',
    equipment_serial: '',
    warranty_id: null,
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
        equipment_serial: formData.equipment_serial || null,
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
      setQuery('');
      setMatches(null);
      setPicked(null);
      setFormData((prev) => ({ ...prev, equipment_serial: '', warranty_id: null, title: '', description: '' }));
      loadData();
    } catch (err) {
      addToast(`Ticket creation failed: ${err.message}`, 'error');
    } finally {
      setSubmitting(false);
    }
  };

  // Dialog for choosing a technician by hand (tickets are normally assigned automatically)
  const [step, setStep] = useState(null); // { kind: 'assign', ticket }
  const [technicians, setTechnicians] = useState([]);
  const [stepForm, setStepForm] = useState({ technician_id: '', needs_replacement: false, notes: '', serial: '' });

  const openStep = async (kind, ticket) => {
    setStepForm({ technician_id: ticket.technician_id || '', needs_replacement: false, notes: '', serial: '' });
    setStep({ kind, ticket });
    try {
      if (kind === 'assign') setTechnicians(await api.getTicketTechnicians());
    } catch (err) {
      addToast(`Error: ${err.message}`, 'error');
    }
  };

  const submitStep = async (e) => {
    e.preventDefault();
    const { kind, ticket } = step;
    try {
      setSubmitting(true);
      if (kind === 'assign') {
        await api.assignTicket(ticket.id, Number(stepForm.technician_id));
        addToast(`Technician assigned to TCK-${String(ticket.id).padStart(4, '0')}. The customer has been told.`, 'success');
      }
      setStep(null);
      loadData();
    } catch (err) {
      addToast(`Error: ${err.message}`, 'error', 6000);
    } finally {
      setSubmitting(false);
    }
  };

  const handleQuote = async (ticket, approved) => {
    try {
      await api.decideTicketQuote(ticket.id, approved);
      addToast(approved ? 'Quotation approved. The repair can go ahead.' : 'Quotation rejected. The ticket is closed with no charge.', approved ? 'success' : 'info');
      loadData();
    } catch (err) {
      addToast(`Error: ${err.message}`, 'error');
    }
  };

  const handleResolve = async (ticket) => {
    const id = ticket.id;
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
          {row.technician_name && (
            <div className="text-[11px] text-slate-500 mt-0.5 flex items-center gap-1"><UserCheck className="w-3 h-3" /> {row.technician_name}</div>
          )}
          {row.needs_replacement !== null && row.needs_replacement !== undefined && (
            <div className={`text-[11px] mt-0.5 font-semibold ${row.needs_replacement ? 'text-purple-700' : 'text-emerald-700'}`}>
              Technician: {row.needs_replacement ? 'needs a replacement' : 'repairable on site'}
              {row.inspection_notes && <span className="block font-normal text-slate-500 max-w-xs">{row.inspection_notes}</span>}
            </div>
          )}
          {row.dispatch_serial && !row.replacement_serial && (
            <div className="text-[11px] text-slate-500 mt-0.5">Dispatched <span className="font-mono font-semibold">{row.dispatch_serial}</span></div>
          )}
          {row.replacement_serial && (
            <div className="text-[11px] text-slate-500 mt-0.5">Replaced by <span className="font-mono font-semibold">{row.replacement_serial}</span></div>
          )}
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
            {row.quote_status === 'Rejected' ? (
              <span className="text-slate-500 font-medium text-[11px]">Quotation rejected, no charge</span>
            ) : row.customer_confirmed ? (
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
          {!canManage && <span className="text-xs text-slate-400">Handled by Support</span>}
          {canManage && (row.status === 'Open' || row.status === 'Assigned') && (
            <button
              onClick={() => openStep('assign', row)}
              className="px-2.5 py-1 text-xs font-semibold rounded bg-indigo-600 hover:bg-indigo-700 text-white transition"
            >
              {row.status === 'Open' ? 'Assign technician' : 'Reassign'}
            </button>
          )}
          {canManage && row.status === 'Assigned' && (
            <span className="text-[11px] text-slate-500">Waiting for the technician's report</span>
          )}
          {canManage && row.status === 'Quotation Sent' && (
            <>
              <button onClick={() => handleQuote(row, true)} className="px-2.5 py-1 text-xs font-semibold rounded bg-emerald-600 hover:bg-emerald-700 text-white transition">
                Customer approved
              </button>
              <button onClick={() => handleQuote(row, false)} className="px-2.5 py-1 text-xs font-semibold rounded border border-rose-300 text-rose-700 hover:bg-rose-50 transition">
                Customer rejected
              </button>
            </>
          )}
          {canManage && row.status === 'Awaiting Dispatch' && (
            <span className="text-[11px] text-slate-500">Waiting for the warehouse to dispatch the replacement</span>
          )}
          {canManage && (row.status === 'In Progress' || row.status === 'Dispatched') ? (
            <button
              onClick={() => handleResolve(row)}
              className="px-2.5 py-1 text-xs font-semibold rounded bg-amber-500 hover:bg-amber-600 text-slate-950 transition"
              title={row.status === 'Dispatched' ? 'The technician has fitted the replacement' : 'Mark ticket resolved'}
            >
              {row.status === 'Dispatched' ? 'Fitted, resolve' : 'Resolve'}
            </button>
          ) : null}

          {canManage && row.status === 'Resolved' && !row.customer_confirmed ? (
            <button
              onClick={() => handleCustomerConfirm(row.id)}
              className="px-2.5 py-1 text-xs font-semibold rounded border border-teal-300 text-teal-800 hover:bg-teal-50 transition"
              title="Customer confirmed resolution"
            >
              Confirm
            </button>
          ) : null}

          {canManage && row.status !== 'Closed' ? (
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
          ) : row.status === 'Closed' ? (
            <span className="text-xs text-slate-400 font-semibold">Closed</span>
          ) : null}
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
          <strong>REPAIR FLOW:</strong> warranty check (<strong>COVERED</strong> ₹0 or <strong>BILLABLE</strong>) →
          technician assigned automatically → technician visits and reports repair or replace → for billable tickets, quotation the customer approves or rejects →
          the warehouse dispatches the replacement unit if one is needed → technician fits it, ticket resolved → customer confirms → closed.
          Billable tickets are invoiced only after the customer approved the quotation and the work is done.
        </div>
      </div>

      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
        <div>
          <h3 className="text-lg font-bold text-slate-900">After-Sales Service Tickets</h3>
          <p className="text-xs text-slate-500">Track equipment complaints, evaluate warranty coverage, and bill out-of-warranty repairs.</p>
        </div>
        {canManage && (
          <button
            onClick={() => setIsModalOpen(true)}
            className="inline-flex items-center gap-2 px-3.5 py-2 bg-amber-500 hover:bg-amber-600 text-slate-950 rounded-lg text-sm font-semibold shadow-xs transition"
          >
            <Plus className="w-4 h-4" /> Create Service Ticket
          </button>
        )}
      </div>

      <DataTable
        columns={columns}
        data={tickets}
        searchPlaceholder="Search tickets by title, customer, or serial..."
      />

      {/* Assign / site visit / dispatch */}
      <Modal
        isOpen={!!step}
        onClose={() => setStep(null)}
        title="Assign a technician"
      >
        {step && (
          <form onSubmit={submitStep} className="space-y-4 text-sm">
            <p className="text-xs text-slate-500">
              TCK-{String(step.ticket.id).padStart(4, '0')} · {step.ticket.customer_name} · {step.ticket.equipment_serial}
            </p>

            {step.kind === 'assign' && (
              <select
                required
                value={stepForm.technician_id}
                onChange={(e) => setStepForm({ ...stepForm, technician_id: e.target.value })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg bg-white focus:ring-2 focus:ring-amber-500 focus:outline-none"
              >
                <option value="">Choose a technician</option>
                {technicians.map((t) => <option key={t.id} value={t.id}>{t.name}{t.phone ? ` · ${t.phone}` : ''}</option>)}
              </select>
            )}

            <div className="flex justify-end gap-3 pt-3 border-t border-slate-200">
              <button type="button" onClick={() => setStep(null)} className="px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-100 transition">
                Cancel
              </button>
              <button type="submit" disabled={submitting} className="px-4 py-2 bg-amber-500 hover:bg-amber-600 text-slate-950 font-semibold rounded-lg transition disabled:opacity-50">
                Assign
              </button>
            </div>
          </form>
        )}
      </Modal>

      {/* Create Ticket Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title="Open Service Ticket (With Auto Warranty Lookup)"
      >
        <form onSubmit={handleCreate} className="space-y-4 text-sm">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Find the customer or the unit *</label>
            <div className="flex gap-2">
              <input
                type="search"
                value={query}
                onChange={(e) => { setQuery(serialFromScan(e.target.value)); setPicked(null); setFormData((prev) => ({ ...prev, equipment_serial: '', warranty_id: null })); }}
                placeholder="Phone number, name, address or serial number"
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:outline-none"
              />
              {cameraScanSupported() && (
                <button
                  type="button"
                  onClick={() => setScanning(!scanning)}
                  className="inline-flex items-center gap-1.5 px-3 py-2 border border-slate-300 rounded-lg text-xs font-semibold text-slate-700 hover:bg-slate-100"
                  title="Scan the QR label on the unit"
                >
                  <Camera className="w-4 h-4" /> Scan
                </button>
              )}
            </div>
            {scanning && (
              <div className="mt-2">
                <CameraScanner
                  onScan={(raw) => {
                    setQuery(serialFromScan(raw));
                    setPicked(null);
                    setFormData((prev) => ({ ...prev, equipment_serial: '', warranty_id: null }));
                    setScanning(false);
                  }}
                  onClose={() => setScanning(false)}
                />
              </div>
            )}

            {picked && (
              <div className="mt-2 p-2.5 rounded-lg border border-emerald-200 bg-emerald-50 text-xs">
                <span className="font-semibold text-slate-900">{picked.customer.name}</span> · {picked.item.product_name} ·{' '}
                <span className="font-mono font-bold">{picked.item.serial_number}</span>
                <span className={`ml-2 px-1.5 py-0.5 rounded font-semibold ${picked.item.under_warranty ? 'bg-emerald-200 text-emerald-900' : 'bg-rose-100 text-rose-800'}`}>
                  {picked.item.under_warranty ? `Under warranty until ${picked.item.warranty_end}` : 'Out of warranty: will be billed'}
                </span>
              </div>
            )}

            {!picked && matches && (
              <div className="mt-2 max-h-56 overflow-y-auto border border-slate-200 rounded-lg divide-y divide-slate-100">
                {matches.length === 0 && <p className="p-3 text-xs text-slate-500">No customer or serial number matches that.</p>}
                {matches.map((c) => (
                  <div key={c.id} className="p-2.5">
                    <div className="text-xs font-semibold text-slate-900">{c.name} <span className="font-normal text-slate-500">· {c.phone} · {c.address}</span></div>
                    {c.equipment.length === 0 && <div className="text-[11px] text-slate-500 mt-1">No delivered equipment yet.</div>}
                    <div className="mt-1.5 flex flex-wrap gap-1.5">
                      {c.equipment.map((item) => (
                        <button
                          key={item.serial_number || `panels-${item.warranty_id}`}
                          type="button"
                          onClick={() => chooseEquipment(c, item)}
                          className="text-left px-2 py-1 rounded border border-slate-300 hover:border-amber-500 hover:bg-amber-50"
                        >
                          <span className="block text-[11px] font-semibold text-slate-800">{item.product_name}</span>
                          <span className="block font-mono text-[11px] text-slate-600">{item.serial_number || 'Solar panels (no serial numbers)'}</span>
                          <span className={`block text-[10px] font-semibold ${item.under_warranty ? 'text-emerald-700' : 'text-rose-700'}`}>
                            {item.under_warranty ? `Warranty to ${item.warranty_end}` : 'No warranty'}
                          </span>
                        </button>
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Ticket Title / Fault Summary *</label>
            <input maxLength={255}
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
            <textarea maxLength={2000}
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
              disabled={submitting || !(formData.equipment_serial || formData.warranty_id)}
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
