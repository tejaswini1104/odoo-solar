import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import DataTable from '../components/DataTable';
import StatusBadge from '../components/StatusBadge';
import Modal from '../components/Modal';
import { LoadingState, ErrorState } from '../components/States';
import { useToast } from '../components/Toast';
import { CreditCard, CheckCircle2, AlertCircle, ShieldCheck, ShoppingCart, ArrowRight } from 'lucide-react';
import { useAuth } from '../auth/AuthContext';

export default function SalesOrders({ setActiveTab }) {
  const { user } = useAuth();
  const isSales = user?.role === 'sales'; // only Sales record payments, verify them and confirm orders
  const [orders, setOrders] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [paymentModalOrder, setPaymentModalOrder] = useState(null);
  const [paymentData, setPaymentData] = useState({
    amount: '',
    payment_type: 'advance',
    reference_notes: ''
  });
  const [submittingPayment, setSubmittingPayment] = useState(false);
  const [pendingPayments, setPendingPayments] = useState([]);
  const { addToast } = useToast();

  const fetchOrders = async () => {
    try {
      setLoading(true);
      setError(null);
      const [data, payments] = await Promise.all([api.getOrders(), api.getPayments()]);
      setOrders(data);
      // Order payments only. Repair invoice payments are verified by Support on the Invoices screen.
      setPendingPayments(payments.filter((p) => p.status === 'Pending Verification' && p.order_id));
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOrders();
  }, []);

  const handleOpenPayment = (order) => {
    setPaymentModalOrder(order);
    // suggest 30% advance
    const suggestedAdvance = Math.round(order.total_amount * 0.3);
    setPaymentData({
      amount: suggestedAdvance,
      payment_type: 'advance',
      reference_notes: `Advance for SO-${order.id.toString().padStart(4, '0')}`
    });
  };

  const handleRecordPayment = async (e) => {
    e.preventDefault();
    if (!paymentModalOrder) return;
    try {
      setSubmittingPayment(true);
      await api.createPayment({
        order_id: paymentModalOrder.id,
        customer_id: paymentModalOrder.customer_id,
        amount: parseFloat(paymentData.amount),
        payment_type: paymentData.payment_type,
        reference_notes: paymentData.reference_notes
      });
      addToast(`Payment of ₹${parseFloat(paymentData.amount).toLocaleString()} recorded successfully!`, 'success');
      setPaymentModalOrder(null);
      fetchOrders();
    } catch (err) {
      addToast(`Payment recording failed: ${err.message}`, 'error');
    } finally {
      setSubmittingPayment(false);
    }
  };

  // Before the hardware leaves the warehouse an order can still be cancelled; stock and the job are released
  const handleCancelOrder = async (order) => {
    const reason = window.prompt(`Why is order SO-${String(order.id).padStart(4, '0')} being cancelled?`);
    if (reason === null) return;
    if (reason.trim().length < 3) {
      addToast('Please give a short reason for the cancellation.', 'error');
      return;
    }
    try {
      await api.cancelOrder(order.id, reason.trim());
      addToast(`Order SO-${String(order.id).padStart(4, '0')} cancelled. Reserved stock is free again and the installation job was removed.${order.advance_paid > 0 ? ` Refund the customer ₹${order.advance_paid.toLocaleString()}.` : ''}`, 'success', 8000);
      fetchOrders();
    } catch (err) {
      addToast(`Could not cancel: ${err.message}`, 'error', 6000);
    }
  };

  const handleConfirmOrder = async (orderId) => {
    try {
      const confirmed = await api.confirmOrder(orderId);
      addToast(
        `Order #${confirmed.id} Confirmed! Inventory reserved and Installation job created automatically.`,
        'success',
        6000
      );
      fetchOrders();
    } catch (err) {
      // Backend hard gate will reject if no advance payment or unapproved survey
      addToast(`Confirmation Rejected: ${err.message}`, 'error', 6000);
    }
  };

  const handleVerifyPayment = async (paymentId) => {
    try {
      await api.verifyPayment(paymentId);
      addToast('Payment verified. It now counts towards the advance.', 'success');
      fetchOrders();
    } catch (err) {
      addToast(`Verification failed: ${err.message}`, 'error');
    }
  };

  const columns = [
    {
      header: 'Order ID & Customer',
      accessor: 'id',
      render: (row) => (
        <div>
          <span className="font-mono text-xs font-bold text-slate-800">SO-{row.id.toString().padStart(4, '0')}</span>
          <div className="font-semibold text-slate-900 mt-0.5">{row.customer_name}</div>
          <div className="text-[11px] text-slate-400">QT-{row.quotation_id.toString().padStart(4, '0')}</div>
        </div>
      )
    },
    {
      header: 'System Package',
      accessor: 'package_name',
      render: (row) => <span className="text-xs font-medium text-slate-800">{row.package_name}</span>
    },
    {
      header: 'Order Value & Payments',
      accessor: 'total_amount',
      render: (row) => (
        <div className="text-xs">
          <div className="font-bold text-slate-900">Total: ₹{row.total_amount?.toLocaleString()}</div>
          <div className="text-slate-600 font-medium mt-0.5">
            Advance: ₹{row.advance_paid?.toLocaleString()}
          </div>
          {row.is_advance_paid ? (
            <span className="text-[10px] text-emerald-600 font-semibold">✓ Advance Recorded</span>
          ) : (
            <span className="text-[10px] text-rose-500 font-semibold">⚠ Payment Pending</span>
          )}
        </div>
      )
    },
    {
      header: 'Survey Gate',
      accessor: 'survey_approved',
      render: (row) => (
        <span className={`px-2 py-0.5 rounded text-xs font-semibold ${row.survey_approved ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-rose-50 text-rose-700 border border-rose-200'}`}>
          {row.survey_approved ? 'Approved' : 'Unapproved'}
        </span>
      )
    },
    {
      header: 'Order Status',
      accessor: 'status',
      render: (row) => <StatusBadge status={row.status} />
    },
    {
      header: 'Actions',
      accessor: 'id',
      render: (row) => (
        <div className="flex items-center gap-2">
          {(row.status === 'Pending Confirmation' || row.status === 'Draft') && !isSales ? (
            <span className="text-xs text-slate-500 font-medium">Awaiting Sales</span>
          ) : row.status === 'Pending Confirmation' || row.status === 'Draft' ? (
            <>
              <button
                onClick={() => handleOpenPayment(row)}
                className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded border border-slate-300 hover:bg-slate-100 text-slate-700 transition"
              >
                <CreditCard className="w-3.5 h-3.5" /> Record Payment
              </button>
              <button
                onClick={() => handleConfirmOrder(row.id)}
                className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-semibold rounded bg-emerald-600 hover:bg-emerald-700 text-white transition shadow-xs"
                title="Requires Approved Survey + Advance Payment"
              >
                <CheckCircle2 className="w-3.5 h-3.5" /> Confirm Order
              </button>
              <button
                onClick={() => handleCancelOrder(row)}
                className="px-2 py-1 text-xs font-semibold rounded border border-rose-300 text-rose-700 hover:bg-rose-50 transition"
              >
                Cancel
              </button>
            </>
          ) : row.status === 'Confirmed' && isSales ? (
            <>
              <span className="text-xs text-slate-500 font-medium">Order Confirmed</span>
              <button
                onClick={() => handleCancelOrder(row)}
                className="px-2 py-1 text-xs font-semibold rounded border border-rose-300 text-rose-700 hover:bg-rose-50 transition"
              >
                Cancel
              </button>
            </>
          ) : (
            <span className="text-xs text-slate-500 font-medium">{row.status === 'Cancelled' ? 'Cancelled' : 'Order Confirmed'}</span>
          )}
        </div>
      )
    }
  ];

  if (loading) return <LoadingState message="Loading sales orders..." />;
  if (error) return <ErrorState title="Failed to load orders" message={error} onRetry={fetchOrders} />;

  return (
    <div className="space-y-4">
      {/* Notice Banner */}
      <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-3.5 text-xs text-emerald-900 flex items-start gap-3">
        <ShieldCheck className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />
        <div>
          <strong>AUTOMATION UPON ORDER CONFIRMATION:</strong> Confirming an order checks that the survey is Approved
          and at least an advance payment is recorded. In an atomic DB transaction, it reserves inventory quantities,
          creates an Installation job record, and assigns a technician.
        </div>
      </div>

      <div className="flex justify-between items-center">
        <div>
          <h3 className="text-lg font-bold text-slate-900">Sales Orders & Payments</h3>
          <p className="text-xs text-slate-500">Record customer advance payments and confirm orders to trigger inventory reservation.</p>
        </div>
      </div>

      {pendingPayments.length > 0 && (
        <div className="bg-white rounded-xl border border-amber-200 p-4">
          <h4 className="text-sm font-bold text-slate-900 mb-1">Customer payments waiting for verification</h4>
          <p className="text-xs text-slate-500 mb-3">Check each reference against the bank statement, then verify it.</p>
          <table className="w-full text-xs">
            <thead className="text-left text-slate-500">
              <tr>
                <th className="py-1.5">Reference</th>
                <th className="py-1.5">Order</th>
                <th className="py-1.5 text-right">Amount</th>
                <th className="py-1.5 text-right">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {pendingPayments.map((p) => (
                <tr key={p.id}>
                  <td className="py-1.5 font-mono">{p.reference_number || '-'}</td>
                  <td className="py-1.5 font-mono">{p.order_id ? `SO-${p.order_id.toString().padStart(4, '0')}` : '-'}</td>
                  <td className="py-1.5 text-right">₹{p.amount.toLocaleString('en-IN')}</td>
                  <td className="py-1.5 text-right">
                    {isSales ? (
                      <button
                        onClick={() => handleVerifyPayment(p.id)}
                        className="px-2.5 py-1 text-xs font-semibold rounded bg-emerald-600 hover:bg-emerald-700 text-white transition"
                      >
                        Verify
                      </button>
                    ) : (
                      <span className="text-slate-400">Sales verify</span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <DataTable
        columns={columns}
        data={orders}
        searchPlaceholder="Search orders by customer or package..."
      />

      {/* Record Payment Modal */}
      <Modal
        isOpen={!!paymentModalOrder}
        onClose={() => setPaymentModalOrder(null)}
        title={paymentModalOrder ? `Record Payment: SO-${paymentModalOrder.id.toString().padStart(4, '0')} (${paymentModalOrder.customer_name})` : 'Payment'}
      >
        {paymentModalOrder && (
          <form onSubmit={handleRecordPayment} className="space-y-4 text-sm">
            <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 text-xs">
              <div className="flex justify-between">
                <span className="text-slate-500">Total Order Amount:</span>
                <span className="font-bold text-slate-900">₹{paymentModalOrder.total_amount?.toLocaleString()}</span>
              </div>
              <div className="flex justify-between mt-1">
                <span className="text-slate-500">Advance Paid So Far:</span>
                <span className="font-semibold text-emerald-600">₹{paymentModalOrder.advance_paid?.toLocaleString()}</span>
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Payment Amount (₹) *</label>
              <input max="10000000"
                required
                type="number"
                min="0.01"
                step="0.01"
                value={paymentData.amount}
                onChange={(e) => setPaymentData({ ...paymentData, amount: e.target.value })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Payment Type *</label>
              <select
                value={paymentData.payment_type}
                onChange={(e) => setPaymentData({ ...paymentData, payment_type: e.target.value })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:outline-none bg-white"
              >
                <option value="advance">Advance Payment (Enables Order Confirmation)</option>
                <option value="full">Full Payment</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Bank Reference / Notes</label>
              <input maxLength={500}
                type="text"
                value={paymentData.reference_notes}
                onChange={(e) => setPaymentData({ ...paymentData, reference_notes: e.target.value })}
                placeholder="e.g. NEFT ref #89283742 or Cash receipt"
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:outline-none"
              />
            </div>

            <div className="flex justify-end gap-3 pt-4 border-t border-slate-200">
              <button
                type="button"
                onClick={() => setPaymentModalOrder(null)}
                className="px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-100 transition"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={submittingPayment}
                className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold rounded-lg transition disabled:opacity-50"
              >
                {submittingPayment ? 'Recording...' : 'Save Payment Record'}
              </button>
            </div>
          </form>
        )}
      </Modal>
    </div>
  );
}
