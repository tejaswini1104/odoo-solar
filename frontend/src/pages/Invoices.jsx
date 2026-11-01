import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import DataTable from '../components/DataTable';
import StatusBadge from '../components/StatusBadge';
import Modal from '../components/Modal';
import { LoadingState, ErrorState } from '../components/States';
import { useToast } from '../components/Toast';
import { Receipt, Edit3, CheckCircle2, Eye, Plus, Trash2 } from 'lucide-react';
import { Printer } from 'lucide-react';
import { printInvoice } from '../utils/printDocument';
import { useAuth } from '../auth/AuthContext';

export default function Invoices() {
  const { user } = useAuth();
  // Repair invoices (tied to a ticket) are handled by Support. Installation invoices are handled by Sales.
  const canHandle = (invoice) => (invoice.ticket_id ? user?.role === 'support' : user?.role === 'sales');
  const [pendingRepairPayments, setPendingRepairPayments] = useState([]);
  const [invoices, setInvoices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedInvoice, setSelectedInvoice] = useState(null);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [editingItems, setEditingItems] = useState([]);
  const [savingItems, setSavingItems] = useState(false);
  const { addToast } = useToast();

  const fetchInvoices = async () => {
    try {
      setLoading(true);
      setError(null);
      const [data, payments] = await Promise.all([api.getInvoices(), api.getPayments()]);
      setInvoices(data);
      setPendingRepairPayments(payments.filter((p) => p.status === 'Pending Verification' && p.invoice_id));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchInvoices();
  }, []);

  const handleOpenEdit = (inv) => {
    setSelectedInvoice(inv);
    setEditingItems(
      inv.items.map((it) => ({
        description: it.description,
        quantity: it.quantity,
        unit_price: it.unit_price
      }))
    );
    setIsEditModalOpen(true);
  };

  const handleAddItemRow = () => {
    setEditingItems([
      ...editingItems,
      { description: 'Replacement Component / Service', quantity: 1, unit_price: 1000 }
    ]);
  };

  const handleRemoveItemRow = (index) => {
    setEditingItems(editingItems.filter((_, i) => i !== index));
  };

  const handleSaveItems = async (e) => {
    e.preventDefault();
    if (!selectedInvoice) return;
    try {
      setSavingItems(true);
      const updated = await api.updateInvoiceItems(selectedInvoice.id, editingItems);
      addToast(`Invoice ${updated.invoice_number} items and totals updated!`, 'success');
      setIsEditModalOpen(false);
      fetchInvoices();
    } catch (err) {
      addToast(`Update failed: ${err.message}`, 'error');
    } finally {
      setSavingItems(false);
    }
  };

  const handleSend = async (invId) => {
    try {
      await api.sendInvoice(invId);
      addToast('Invoice sent. The customer can now see it in their portal.', 'success');
      fetchInvoices();
    } catch (err) {
      addToast(`Could not send: ${err.message}`, 'error', 6000);
    }
  };

  const handleVerifyPayment = async (paymentId) => {
    try {
      await api.verifyPayment(paymentId);
      addToast('Payment verified. The invoice is marked Paid once it is fully covered.', 'success');
      fetchInvoices();
    } catch (err) {
      addToast(`Verification failed: ${err.message}`, 'error', 6000);
    }
  };

  const handleMarkPaid = async (invId) => {
    try {
      await api.markInvoicePaid(invId);
      addToast(`Invoice marked as PAID!`, 'success');
      fetchInvoices();
    } catch (err) {
      addToast(`Action failed: ${err.message}`, 'error');
    }
  };

  const columns = [
    {
      header: 'Invoice #',
      accessor: 'invoice_number',
      render: (row) => (
        <span className="font-mono text-xs font-bold text-slate-800 bg-slate-100 px-2 py-0.5 rounded border border-slate-200">
          {row.invoice_number}
        </span>
      )
    },
    {
      header: 'Customer',
      accessor: 'customer_name',
      render: (row) => <span className="font-semibold text-slate-900 text-xs">{row.customer_name}</span>
    },
    {
      header: 'Origin & Linkage',
      accessor: 'ticket_id',
      render: (row) => (
        <div className="text-xs">
          {row.ticket_id ? (
            <span className="text-purple-700 font-semibold bg-purple-50 px-2 py-0.5 rounded border border-purple-200">
              Service Ticket TCK-{row.ticket_id.toString().padStart(4, '0')} (Billable)
            </span>
          ) : row.order_id ? (
            <span className="text-blue-700 font-medium bg-blue-50 px-2 py-0.5 rounded border border-blue-200">
              Sales Order SO-{row.order_id.toString().padStart(4, '0')}
            </span>
          ) : (
            <span className="text-slate-500">Direct</span>
          )}
        </div>
      )
    },
    {
      header: 'Amount Breakdown',
      accessor: 'total',
      render: (row) => (
        <div className="text-xs">
          <div className="font-bold text-slate-900 text-sm">₹{row.total?.toLocaleString()}</div>
          <div className="text-slate-500 text-[11px]">Subtotal: ₹{row.subtotal?.toLocaleString()} + 18% GST</div>
        </div>
      )
    },
    {
      header: 'Invoice Status',
      accessor: 'status',
      render: (row) => <StatusBadge status={row.status} />
    },
    {
      header: 'Actions',
      accessor: 'id',
      render: (row) => (
        <div className="flex items-center gap-1.5">
          {!canHandle(row) && (
            <span className="text-xs text-slate-400">
              {row.ticket_id ? 'Handled by Support' : 'Handled by Sales'}
            </span>
          )}
          {canHandle(row) && row.status === 'Draft' && (
          <button
            onClick={() => handleOpenEdit(row)}
            className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded border border-slate-300 hover:bg-slate-100 text-slate-700 transition"
            title="Edit draft line items"
          >
            <Edit3 className="w-3.5 h-3.5" /> Edit Items
          </button>
          )}
          <button
            onClick={() => printInvoice(row)}
            className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded border border-slate-300 hover:bg-slate-100 text-slate-700 transition"
            title="Print, or save as PDF to send to the customer"
          >
            <Printer className="w-3.5 h-3.5" /> PDF
          </button>
          {canHandle(row) && row.status === 'Draft' && (
            <button
              onClick={() => handleSend(row.id)}
              className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-semibold rounded bg-slate-900 hover:bg-slate-800 text-white transition"
              title="Make this invoice visible to the customer. A repair invoice can be sent once its ticket is resolved."
            >
              Send to customer
            </button>
          )}
          {canHandle(row) && row.status !== 'Paid' && (
            <button
              onClick={() => handleMarkPaid(row.id)}
              className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-semibold rounded bg-emerald-600 hover:bg-emerald-700 text-white transition"
              title="Mark Paid"
            >
              <CheckCircle2 className="w-3.5 h-3.5" /> Mark Paid
            </button>
          )}
        </div>
      )
    }
  ];

  if (loading) return <LoadingState message="Loading invoices..." />;
  if (error) return <ErrorState title="Failed to load invoices" message={error} onRetry={fetchInvoices} />;

  return (
    <div className="space-y-4">
      <div>
        <h3 className="text-lg font-bold text-slate-900">Billing & Invoices</h3>
        <p className="text-xs text-slate-500">
          Structured records generated for out-of-warranty billable service calls and project milestones.
        </p>
      </div>

      {pendingRepairPayments.length > 0 && (user?.role === 'support' || user?.role === 'admin') && (
        <div className="bg-white rounded-xl border border-amber-200 p-4">
          <h4 className="text-sm font-bold text-slate-900 mb-1">Repair payments waiting for verification</h4>
          <p className="text-xs text-slate-500 mb-3">Check each reference against the bank statement, then verify it.</p>
          <table className="w-full text-xs">
            <thead className="text-left text-slate-500">
              <tr>
                <th className="py-1.5">Reference</th>
                <th className="py-1.5">Invoice</th>
                <th className="py-1.5 text-right">Amount</th>
                <th className="py-1.5 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {pendingRepairPayments.map((p) => {
                const invoice = invoices.find((i) => i.id === p.invoice_id);
                return (
                  <tr key={p.id}>
                    <td className="py-1.5 font-mono">{p.reference_number || '-'}</td>
                    <td className="py-1.5 font-mono">{invoice ? invoice.invoice_number : `#${p.invoice_id}`}</td>
                    <td className="py-1.5 text-right">₹{p.amount.toLocaleString('en-IN')}</td>
                    <td className="py-1.5 text-right">
                      {user?.role === 'support' ? (
                        <button
                          onClick={() => handleVerifyPayment(p.id)}
                          className="px-2.5 py-1 text-xs font-semibold rounded bg-emerald-600 hover:bg-emerald-700 text-white transition"
                        >
                          Verify
                        </button>
                      ) : (
                        <span className="text-slate-400">Support verify</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      <DataTable
        columns={columns}
        data={invoices}
        searchPlaceholder="Search invoices by number or customer..."
      />

      {/* Edit Line Items Modal */}
      <Modal
        isOpen={isEditModalOpen}
        onClose={() => setIsEditModalOpen(false)}
        title={selectedInvoice ? `Edit Items for ${selectedInvoice.invoice_number}` : 'Invoice Items'}
        maxWidth="max-w-2xl"
      >
        <form onSubmit={handleSaveItems} className="space-y-4 text-sm">
          <p className="text-xs text-slate-500">
            Admins can edit placeholder repair parts and technician labour fee lines. Subtotal, 18% GST, and totals update automatically.
          </p>

          <div className="space-y-2">
            {editingItems.map((item, index) => (
              <div key={index} className="flex gap-2 items-center bg-slate-50 p-2 rounded-lg border border-slate-200">
                <input maxLength={2000}
                  required
                  type="text"
                  placeholder="Line Item Description"
                  value={item.description}
                  onChange={(e) => {
                    const copy = [...editingItems];
                    copy[index].description = e.target.value;
                    setEditingItems(copy);
                  }}
                  className="flex-1 px-2.5 py-1.5 border border-slate-300 rounded text-xs bg-white focus:ring-1 focus:ring-amber-500"
                />
                <input max="1000"
                  required
                  type="number"
                  min="1"
                  placeholder="Qty"
                  value={item.quantity}
                  onChange={(e) => {
                    const copy = [...editingItems];
                    copy[index].quantity = parseInt(e.target.value) || 1;
                    setEditingItems(copy);
                  }}
                  className="w-16 px-2 py-1.5 border border-slate-300 rounded text-xs bg-white text-center focus:ring-1 focus:ring-amber-500"
                />
                <input max="10000000"
                  required
                  type="number"
                  step="50"
                  min="0"
                  placeholder="Unit Price (₹)"
                  value={item.unit_price}
                  onChange={(e) => {
                    const copy = [...editingItems];
                    copy[index].unit_price = parseFloat(e.target.value) || 0;
                    setEditingItems(copy);
                  }}
                  className="w-28 px-2.5 py-1.5 border border-slate-300 rounded text-xs bg-white text-right focus:ring-1 focus:ring-amber-500"
                />
                <button
                  type="button"
                  onClick={() => handleRemoveItemRow(index)}
                  className="p-1.5 text-slate-400 hover:text-rose-600 rounded transition"
                  title="Remove Line"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>

          <button
            type="button"
            onClick={handleAddItemRow}
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-amber-700 hover:text-amber-800"
          >
            <Plus className="w-3.5 h-3.5" /> Add Another Line Item
          </button>

          <div className="flex justify-end gap-3 pt-4 border-t border-slate-200">
            <button
              type="button"
              onClick={() => setIsEditModalOpen(false)}
              className="px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-100 transition text-xs"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={savingItems}
              className="px-4 py-2 bg-amber-500 hover:bg-amber-600 text-slate-950 font-semibold rounded-lg transition text-xs disabled:opacity-50"
            >
              {savingItems ? 'Saving...' : 'Save Updated Invoice'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
