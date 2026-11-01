import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import StatusBadge from '../components/StatusBadge';
import { LoadingState, ErrorState, EmptyState } from '../components/States';
import { useToast } from '../components/Toast';
import { useAuth } from '../auth/AuthContext';
import { printInvoice } from '../utils/printDocument';

const rupees = (n) => `₹${Number(n || 0).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

function PayInvoiceForm({ invoice, onPaid }) {
  const [amount, setAmount] = useState(invoice.payable_now.toFixed(2));
  const [reference, setReference] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const { addToast } = useToast();

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      setSubmitting(true);
      await api.payInvoice(invoice.id, { amount: Number(amount), reference_number: reference.trim() });
      addToast('Payment reported. We will confirm it once it reaches our bank account.', 'success', 6000);
      setReference('');
      onPaid();
    } catch (err) {
      addToast(`Could not report payment: ${err.message}`, 'error', 6000);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex flex-wrap items-end gap-3 text-xs pt-3 border-t border-slate-100">
      <div>
        <label className="block font-semibold text-slate-700 mb-1">Amount transferred (₹)</label>
        <input max="10000000"
          required
          type="number"
          min="0.01"
          step="0.01"
          value={amount}
          onChange={(e) => setAmount(e.target.value)}
          className="w-36 px-2.5 py-1.5 border border-slate-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:outline-none"
        />
      </div>
      <div>
        <label className="block font-semibold text-slate-700 mb-1">Bank reference / UTR</label>
        <input
          required
          type="text"
          minLength={4}
          maxLength={100}
          value={reference}
          onChange={(e) => setReference(e.target.value)}
          className="w-56 px-2.5 py-1.5 border border-slate-300 rounded-lg font-mono focus:ring-2 focus:ring-amber-500 focus:outline-none"
        />
      </div>
      <button
        type="submit"
        disabled={submitting}
        className="px-3 py-2 font-semibold rounded-lg bg-amber-500 hover:bg-amber-600 text-slate-950 transition disabled:opacity-50"
      >
        {submitting ? 'Sending...' : 'Report payment'}
      </button>
    </form>
  );
}

export default function PortalInvoices() {
  const { user } = useAuth();
  const [invoices, setInvoices] = useState([]);
  const [bank, setBank] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = async () => {
    try {
      setLoading(true);
      setError(null);
      const [invoiceData, bankData] = await Promise.all([api.getMyInvoices(), api.getBankDetails()]);
      setInvoices(invoiceData);
      setBank(bankData);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  if (loading) return <LoadingState message="Loading your invoices..." />;
  if (error) return <ErrorState title="Could not load invoices" message={error} onRetry={load} />;
  if (invoices.length === 0) {
    return (
      <EmptyState
        title="No invoices yet"
        description="Your installation invoice appears after your payments are complete. Repair invoices appear once a repair is finished."
      />
    );
  }

  const hasUnpaid = invoices.some((inv) => inv.status === 'Sent');

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-bold text-slate-900">My invoices</h2>
        <p className="text-xs text-slate-500">All amounts include GST.</p>
      </div>

      {hasUnpaid && bank && (
        <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 text-xs text-amber-950">
          <strong>Pay by bank transfer:</strong> {bank.account_name}, {bank.bank_name}, account{' '}
          <span className="font-mono font-semibold">{bank.account_number}</span>, IFSC{' '}
          <span className="font-mono font-semibold">{bank.ifsc}</span>, UPI{' '}
          <span className="font-mono font-semibold">{bank.upi_id}</span>. Then report the payment under the invoice.
        </div>
      )}

      {invoices.map((inv) => (
        <div key={inv.id} className="bg-white rounded-xl border border-slate-200 p-5 space-y-3">
          <div className="flex items-center justify-between">
            <div>
              <div className="font-mono text-xs font-bold text-slate-700">{inv.invoice_number}</div>
              <div className="text-xs text-slate-500">{inv.origin}</div>
            </div>
            <div className="flex items-center gap-3">
              <button
                onClick={() => printInvoice({ ...inv, tax: inv.gst, created_at: new Date().toISOString(), ticket_id: null }, user?.name)}
                className="text-xs font-semibold text-slate-700 hover:text-slate-900 underline"
              >
                Print / PDF
              </button>
              <StatusBadge status={inv.status === 'Sent' ? 'Open' : inv.status} />
            </div>
          </div>

          <table className="w-full text-xs">
            <thead className="text-left text-slate-500">
              <tr>
                <th className="py-1.5">Item</th>
                <th className="py-1.5 text-right">Qty</th>
                <th className="py-1.5 text-right">Unit price</th>
                <th className="py-1.5 text-right">Amount</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {inv.items.map((item, idx) => (
                <tr key={idx}>
                  <td className="py-1.5 text-slate-800">{item.description}</td>
                  <td className="py-1.5 text-right">{item.quantity}</td>
                  <td className="py-1.5 text-right">{rupees(item.unit_price)}</td>
                  <td className="py-1.5 text-right">{rupees(item.total)}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <div className="flex flex-wrap gap-x-6 gap-y-1 text-xs text-slate-600">
            <span>Subtotal: <strong>{rupees(inv.subtotal)}</strong></span>
            <span>GST (18%): <strong>{rupees(inv.gst)}</strong></span>
            <span>Total: <strong className="text-slate-900">{rupees(inv.total)}</strong></span>
            {inv.status === 'Sent' && (
              <>
                {inv.paid_verified > 0 && <span>Paid: <strong>{rupees(inv.paid_verified)}</strong></span>}
                {inv.paid_pending > 0 && <span>Waiting for us to check: <strong>{rupees(inv.paid_pending)}</strong></span>}
              </>
            )}
          </div>

          {inv.status === 'Sent' && inv.payable_now > 0 && <PayInvoiceForm invoice={inv} onPaid={load} />}
        </div>
      ))}
    </div>
  );
}
