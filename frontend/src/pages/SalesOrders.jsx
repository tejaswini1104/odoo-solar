import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import DataTable from '../components/DataTable';
import StatusBadge from '../components/StatusBadge';
import Modal from '../components/Modal';
import { LoadingState, ErrorState } from '../components/States';
import { useToast } from '../components/Toast';
import { CreditCard, CheckCircle2, AlertCircle, ShieldCheck, ShoppingCart, ArrowRight } from 'lucide-react';

export default function SalesOrders({ setActiveTab }) {
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
  const { addToast } = useToast();

  const fetchOrders = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.getOrders();
      setOrders(data);
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
          {row.status === 'Pending Confirmation' || row.status === 'Draft' ? (
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
            </>
          ) : (
            <span className="text-xs text-slate-500 font-medium">Order Confirmed</span>
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
              <input
                required
                type="number"
                min="1"
                step="100"
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
              <input
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
