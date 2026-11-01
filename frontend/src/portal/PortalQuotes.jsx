import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api/client';
import { LoadingState, ErrorState, EmptyState } from '../components/States';
import { useToast } from '../components/Toast';
import { printQuotation } from '../utils/printDocument';

const rupees = (n) => `₹${Number(n || 0).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

export default function PortalQuotes() {
  const [quotes, setQuotes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [acceptingId, setAcceptingId] = useState(null);
  const { addToast } = useToast();

  const load = async () => {
    try {
      setLoading(true);
      setError(null);
      setQuotes(await api.getPortalQuotations());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const handleAccept = async (quote) => {
    try {
      setAcceptingId(quote.id);
      await api.acceptPortalQuotation(quote.id);
      addToast(`Quotation ${quote.reference} accepted. Please pay the advance to schedule installation.`, 'success', 6000);
      load();
    } catch (err) {
      addToast(`Could not accept: ${err.message}`, 'error', 6000);
    } finally {
      setAcceptingId(null);
    }
  };

  if (loading) return <LoadingState message="Loading your quotations..." />;
  if (error) return <ErrorState title="Could not load quotations" message={error} onRetry={load} />;
  if (quotes.length === 0) {
    return <EmptyState title="No quotations yet" description="Your quotation appears here after our surveyor has visited your roof." />;
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-bold text-slate-900">My quotations</h2>
        <p className="text-xs text-slate-500">All amounts include GST. The advance is {quotes[0].advance_percent}% of the total.</p>
      </div>

      {quotes.map((q) => (
        <div key={q.id} className="bg-white rounded-xl border border-slate-200 p-5 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="font-mono text-xs font-bold text-slate-700">{q.reference}</div>
              <h3 className="font-bold text-slate-900">{q.package_name}</h3>
            </div>
            <span className="text-xs font-semibold px-2.5 py-1 rounded-full bg-slate-100 text-slate-700">
              {q.status === 'Sent' ? 'Awaiting your acceptance' : `Accepted${q.order_status ? ` · ${q.order_status}` : ''}`}
            </span>
          </div>

          <table className="w-full text-xs">
            <thead className="text-slate-500 text-left">
              <tr>
                <th className="py-1.5">Item</th>
                <th className="py-1.5 text-right">Qty</th>
                <th className="py-1.5 text-right">Unit price</th>
                <th className="py-1.5 text-right">Amount</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {q.items.map((item, idx) => (
                <tr key={idx}>
                  <td className="py-1.5 text-slate-800">{item.product_name}</td>
                  <td className="py-1.5 text-right">{item.quantity}</td>
                  <td className="py-1.5 text-right">{rupees(item.unit_price)}</td>
                  <td className="py-1.5 text-right">{rupees(item.line_total)}</td>
                </tr>
              ))}
            </tbody>
          </table>

          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
            <div className="bg-slate-50 rounded-lg p-3">
              <div className="text-slate-500">Subtotal</div>
              <div className="font-semibold text-slate-900">{rupees(q.subtotal)}</div>
            </div>
            <div className="bg-slate-50 rounded-lg p-3">
              <div className="text-slate-500">GST (18%)</div>
              <div className="font-semibold text-slate-900">{rupees(q.gst)}</div>
            </div>
            <div className="bg-slate-50 rounded-lg p-3">
              <div className="text-slate-500">Total incl. GST</div>
              <div className="font-semibold text-slate-900">{rupees(q.total)}</div>
            </div>
            <div className="bg-amber-50 rounded-lg p-3 border border-amber-200">
              <div className="text-amber-800">Advance due ({q.advance_percent}%)</div>
              <div className="font-bold text-slate-900">{rupees(q.advance_required)}</div>
            </div>
          </div>

          <div className="text-xs text-slate-600">
            Verified so far: <strong>{rupees(q.advance_verified)}</strong>
            {q.advance_pending > 0 && <> · Waiting for us to check: <strong>{rupees(q.advance_pending)}</strong></>}
            {' · '}Advance still to pay: <strong>{rupees(q.advance_outstanding)}</strong>
            {' · '}Balance due after installation: <strong>{rupees(q.balance_required)}</strong>
          </div>

          <div className="flex flex-wrap gap-3 pt-2 border-t border-slate-100">
            <button
              onClick={() => printQuotation({
                id: q.id,
                customer_name: null,
                package_name: q.package_name,
                subtotal: q.subtotal,
                tax: q.gst,
                total: q.total,
                created_at: new Date().toISOString(),
                items: q.items.map((it) => ({ product_name: it.product_name, quantity: it.quantity, unit_price: it.unit_price, total_price: it.line_total })),
              })}
              className="px-4 py-2 text-xs font-semibold rounded-lg border border-slate-300 text-slate-700 hover:bg-slate-100 transition"
            >
              Print / PDF
            </button>
            {q.status === 'Sent' && (
              <button
                onClick={() => handleAccept(q)}
                disabled={acceptingId === q.id}
                className="px-4 py-2 text-xs font-semibold rounded-lg bg-amber-500 hover:bg-amber-600 text-slate-950 transition disabled:opacity-50"
              >
                {acceptingId === q.id ? 'Accepting...' : 'Accept quotation'}
              </button>
            )}
            {q.status === 'Accepted' && q.payable_now > 0 && (
              <Link
                to="/portal/payments"
                className="px-4 py-2 text-xs font-semibold rounded-lg bg-slate-900 hover:bg-slate-800 text-white transition"
              >
                {q.order_completed ? 'Pay the balance' : 'Pay the advance'}
              </Link>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
