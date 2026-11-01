import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import StatusBadge from '../components/StatusBadge';
import { LoadingState, ErrorState } from '../components/States';
import { useToast } from '../components/Toast';

const rupees = (n) => `₹${Number(n || 0).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

export default function PortalPayments() {
  const [bank, setBank] = useState(null);
  const [quotes, setQuotes] = useState([]);
  const [payments, setPayments] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState({ quotation_id: '', amount: '', reference_number: '' });
  const { addToast } = useToast();

  const load = async () => {
    try {
      setLoading(true);
      setError(null);
      const [bankData, quoteData, paymentData] = await Promise.all([
        api.getBankDetails(),
        api.getPortalQuotations(),
        api.getMyPayments(),
      ]);
      setBank(bankData);
      setQuotes(quoteData);
      setPayments(paymentData);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  // Only accepted quotations can take an advance
  const payable = quotes.filter((q) => q.status === 'Accepted' && q.payable_now > 0);
  const selected = payable.find((q) => String(q.id) === String(form.quotation_id)) || payable[0];

  const pickQuote = (id) => {
    const quote = payable.find((q) => String(q.id) === String(id));
    setForm({ ...form, quotation_id: id, amount: quote ? quote.payable_now.toFixed(2) : '' });
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    const quoteId = selected ? selected.id : form.quotation_id;
    // The box shows the amount due as a default without storing it, so use what the customer sees
    const amountValue = form.amount === '' && selected ? selected.payable_now.toFixed(2) : form.amount;
    try {
      setSubmitting(true);
      await api.reportPayment({
        quotation_id: Number(quoteId),
        amount: Number(amountValue),
        reference_number: form.reference_number.trim(),
      });
      addToast('Payment reported. We will confirm it once it reaches our bank account.', 'success', 6000);
      setForm({ quotation_id: '', amount: '', reference_number: '' });
      load();
    } catch (err) {
      addToast(`Could not report payment: ${err.message}`, 'error', 6000);
    } finally {
      setSubmitting(false);
    }
  };

  if (loading) return <LoadingState message="Loading payment details..." />;
  if (error) return <ErrorState title="Could not load payments" message={error} onRetry={load} />;

  return (
    <div className="space-y-6">
      <div className="bg-white rounded-xl border border-slate-200 p-5">
        <h2 className="text-lg font-bold text-slate-900">Pay by bank transfer</h2>
        <p className="text-xs text-slate-500 mb-4">
          After you accept a quotation, pay the {bank.advance_percent}% advance or the full amount (both include GST). Any
          balance is due once your installation is complete. Transfer the amount to the account below, then enter it here
          with the bank reference number.
        </p>

        <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-2 text-sm bg-slate-50 rounded-lg p-4 border border-slate-200">
          <dt className="text-slate-500">Account name</dt><dd className="font-semibold text-slate-900">{bank.account_name}</dd>
          <dt className="text-slate-500">Bank</dt><dd className="font-semibold text-slate-900">{bank.bank_name}</dd>
          <dt className="text-slate-500">Account number</dt><dd className="font-mono font-semibold text-slate-900">{bank.account_number}</dd>
          <dt className="text-slate-500">IFSC</dt><dd className="font-mono font-semibold text-slate-900">{bank.ifsc}</dd>
          <dt className="text-slate-500">UPI ID</dt><dd className="font-mono font-semibold text-slate-900">{bank.upi_id}</dd>
        </dl>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 p-5">
        <h3 className="font-bold text-slate-900 mb-3">I have paid</h3>

        {payable.length === 0 ? (
          <p className="text-xs text-slate-500">
            Nothing is payable right now. Accept a quotation first. If you have already paid in full, the payment is
            either confirmed or waiting for us to verify it.
          </p>
        ) : (
          <form onSubmit={handleSubmit} className="space-y-4 text-sm max-w-md">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Quotation</label>
              <select
                value={selected ? selected.id : ''}
                onChange={(e) => pickQuote(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg bg-white focus:ring-2 focus:ring-amber-500 focus:outline-none"
              >
                {payable.map((q) => (
                  <option key={q.id} value={q.id}>{q.reference} · {q.package_name}</option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Amount transferred (₹)</label>
              <input max="10000000"
                required
                type="number"
                min="0.01"
                step="0.01"
                value={form.amount === '' && selected ? selected.payable_now.toFixed(2) : form.amount}
                onChange={(e) => setForm({ ...form, amount: e.target.value })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:outline-none"
              />
              {selected && (
                <p className="text-[11px] text-slate-500 mt-1">You can pay up to {rupees(selected.payable_now)}. The advance needed to confirm your order is {rupees(selected.advance_required)}.</p>
              )}
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Bank reference / UTR number</label>
              <input
                required
                type="text"
                minLength={4}
                maxLength={100}
                value={form.reference_number}
                onChange={(e) => setForm({ ...form, reference_number: e.target.value })}
                placeholder="As shown on your bank receipt"
                className="w-full px-3 py-2 border border-slate-300 rounded-lg font-mono focus:ring-2 focus:ring-amber-500 focus:outline-none"
              />
            </div>

            <button
              type="submit"
              disabled={submitting}
              className="px-4 py-2 bg-amber-500 hover:bg-amber-600 text-slate-950 font-semibold rounded-lg transition disabled:opacity-50"
            >
              {submitting ? 'Sending...' : 'Report payment'}
            </button>
          </form>
        )}
      </div>

      <div className="bg-white rounded-xl border border-slate-200 p-5">
        <h3 className="font-bold text-slate-900 mb-3">My payments</h3>
        {payments.length === 0 ? (
          <p className="text-xs text-slate-500">No payments reported yet.</p>
        ) : (
          <table className="w-full text-xs">
            <thead className="text-left text-slate-500">
              <tr>
                <th className="py-1.5">Date</th>
                <th className="py-1.5">Quotation</th>
                <th className="py-1.5">Reference</th>
                <th className="py-1.5 text-right">Amount</th>
                <th className="py-1.5">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {payments.map((p) => (
                <tr key={p.id}>
                  <td className="py-1.5">{new Date(p.payment_date).toLocaleDateString('en-IN')}</td>
                  <td className="py-1.5 font-mono">{p.quotation_reference}</td>
                  <td className="py-1.5 font-mono">{p.reference_number || '-'}</td>
                  <td className="py-1.5 text-right">{rupees(p.amount)}</td>
                  <td className="py-1.5"><StatusBadge status={p.status === 'Verified' ? 'Paid' : p.status} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
