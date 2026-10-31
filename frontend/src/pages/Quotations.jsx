import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import DataTable from '../components/DataTable';
import StatusBadge from '../components/StatusBadge';
import Modal from '../components/Modal';
import { LoadingState, ErrorState } from '../components/States';
import { useToast } from '../components/Toast';
import { Plus, CheckCircle, FileText, AlertTriangle, ArrowRight, Eye } from 'lucide-react';

export default function Quotations({ setActiveTab }) {
  const [quotations, setQuotations] = useState([]);
  const [customers, setCustomers] = useState([]);
  const [surveys, setSurveys] = useState([]);
  const [packages, setPackages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [selectedQuote, setSelectedQuote] = useState(null);
  const { addToast } = useToast();

  const [formData, setFormData] = useState({
    customer_id: '',
    survey_id: '',
    package_id: ''
  });

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [quoteData, custData, survData, pkgData] = await Promise.all([
        api.getQuotations(),
        api.getCustomers(),
        api.getSurveys(),
        api.getPackages()
      ]);
      setQuotations(quoteData);
      setCustomers(custData);
      setSurveys(survData);
      setPackages(pkgData);

      if (custData.length > 0 && !formData.customer_id) {
        setFormData((prev) => ({
          ...prev,
          customer_id: custData[0].id,
          survey_id: survData[0]?.id || '',
          package_id: pkgData[0]?.id || ''
        }));
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
      const newQuote = await api.createQuotation({
        customer_id: parseInt(formData.customer_id),
        survey_id: parseInt(formData.survey_id),
        package_id: parseInt(formData.package_id)
      });
      addToast(`Quotation #${newQuote.id} generated with automatic BOM! Total: ₹${newQuote.total?.toLocaleString()}`, 'success');
      setIsModalOpen(false);
      loadData();
    } catch (err) {
      // Backend hard gate will reject if survey is not Approved
      addToast(`Quotation Rejected: ${err.message}`, 'error', 6000);
    } finally {
      setSubmitting(false);
    }
  };

  const handleConfirmAndCreateOrder = async (quoteId) => {
    try {
      const order = await api.confirmQuotation(quoteId);
      addToast(`Sales Order #${order.id} generated from Quotation #${quoteId}!`, 'success');
      loadData();
      if (setActiveTab) setActiveTab('orders');
    } catch (err) {
      addToast(`Failed: ${err.message}`, 'error');
    }
  };

  const columns = [
    {
      header: 'Quote ID & Customer',
      accessor: 'id',
      render: (row) => (
        <div>
          <span className="font-mono text-xs font-bold text-slate-800">QT-{row.id.toString().padStart(4, '0')}</span>
          <div className="font-semibold text-slate-900 mt-0.5">{row.customer_name}</div>
        </div>
      )
    },
    {
      header: 'Package & BOM Items',
      accessor: 'package_name',
      render: (row) => (
        <div className="text-xs">
          <div className="font-medium text-slate-800">{row.package_name}</div>
          <span className="text-slate-500">{row.items?.length || 0} automated BOM components</span>
        </div>
      )
    },
    {
      header: 'Linked Site Survey',
      accessor: 'survey_id',
      render: (row) => (
        <div className="text-xs">
          <span className="font-mono font-medium text-slate-700">SURV-{row.survey_id.toString().padStart(4, '0')}</span>
          <div className="text-emerald-600 font-semibold text-[11px]">Approved Hard Gate Passed</div>
        </div>
      )
    },
    {
      header: 'Total Turnkey Price',
      accessor: 'total',
      render: (row) => (
        <div className="text-xs">
          <div className="font-bold text-slate-900 text-sm">₹{row.total?.toLocaleString()}</div>
          <div className="text-slate-500 text-[11px]">Subtotal: ₹{row.subtotal?.toLocaleString()} + 18% GST</div>
        </div>
      )
    },
    {
      header: 'Status',
      accessor: 'status',
      render: (row) => <StatusBadge status={row.status} />
    },
    {
      header: 'Actions',
      accessor: 'id',
      render: (row) => (
        <div className="flex items-center gap-2">
          <button
            onClick={() => setSelectedQuote(row)}
            className="p-1.5 text-slate-600 hover:text-slate-900 rounded hover:bg-slate-100 transition"
            title="View Quotation BOM"
          >
            <Eye className="w-4 h-4" />
          </button>
          {row.status === 'Draft' && (
            <button
              onClick={() => handleConfirmAndCreateOrder(row.id)}
              className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-semibold rounded bg-amber-500 hover:bg-amber-600 text-slate-950 transition"
              title="Accept Quotation & Generate Sales Order"
            >
              <CheckCircle className="w-3.5 h-3.5" /> Accept & Create Order
            </button>
          )}
        </div>
      )
    }
  ];

  if (loading) return <LoadingState message="Loading solar quotations..." />;
  if (error) return <ErrorState title="Failed to load quotations" message={error} onRetry={loadData} />;

  return (
    <div className="space-y-4">
      {/* Hard Gate Callout */}
      <div className="bg-blue-50 border border-blue-200 rounded-xl p-3.5 flex items-center gap-3 text-xs text-blue-900">
        <AlertTriangle className="w-5 h-5 text-blue-600 shrink-0" />
        <div>
          <strong>ENFORCED BACKEND GATE:</strong> You cannot create a quotation for a customer unless their site survey is in
          <strong> Approved</strong> status. Selecting an unapproved survey will trigger a validation error.
        </div>
      </div>

      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
        <div>
          <h3 className="text-lg font-bold text-slate-900">Customer Quotations</h3>
          <p className="text-xs text-slate-500">Automated quotations with turnkey BOM, 18% GST calculation, and sales order creation.</p>
        </div>
        <button
          onClick={() => setIsModalOpen(true)}
          className="inline-flex items-center gap-2 px-3.5 py-2 bg-amber-500 hover:bg-amber-600 text-slate-950 rounded-lg text-sm font-semibold shadow-xs transition"
        >
          <Plus className="w-4 h-4" /> Create Quotation
        </button>
      </div>

      <DataTable
        columns={columns}
        data={quotations}
        searchPlaceholder="Search quotations by customer or package..."
      />

      {/* Create Quotation Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title="Generate Automated Quotation"
      >
        <form onSubmit={handleCreate} className="space-y-4 text-sm">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Select Customer *</label>
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
              Select Site Survey (Approved Gate Required) *
            </label>
            <select
              required
              value={formData.survey_id}
              onChange={(e) => setFormData({ ...formData, survey_id: e.target.value })}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:outline-none bg-white"
            >
              {surveys.map((s) => {
                const cust = customers.find((c) => c.id === s.customer_id);
                return (
                  <option key={s.id} value={s.id}>
                    SURV-{s.id.toString().padStart(4, '0')} - {cust?.name || 'Customer'} | Status: [{s.status}]
                    {s.status === 'Approved' ? ' ✓ APPROVED' : ' ❌ UNAPPROVED'}
                  </option>
                );
              })}
            </select>
            <p className="text-[11px] text-slate-500 mt-1">
              Note: If an unapproved survey is chosen, the backend service layer will explicitly reject it.
            </p>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Select Solar Package *</label>
            <select
              required
              value={formData.package_id}
              onChange={(e) => setFormData({ ...formData, package_id: e.target.value })}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:outline-none bg-white"
            >
              {packages.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name} ({p.capacity_kw} kW {p.system_type}) - ₹{p.base_price?.toLocaleString()}
                </option>
              ))}
            </select>
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
              {submitting ? 'Generating BOM...' : 'Generate Quotation'}
            </button>
          </div>
        </form>
      </Modal>

      {/* View Quotation Modal */}
      <Modal
        isOpen={!!selectedQuote}
        onClose={() => setSelectedQuote(null)}
        title={selectedQuote ? `Quotation QT-${selectedQuote.id.toString().padStart(4, '0')} for ${selectedQuote.customer_name}` : 'Quotation'}
        maxWidth="max-w-3xl"
      >
        {selectedQuote && (
          <div className="space-y-4 text-xs">
            <div className="flex justify-between items-center bg-slate-50 p-3 rounded-lg border border-slate-200">
              <div>
                <span className="text-slate-500">Selected Package: </span>
                <strong className="text-slate-900">{selectedQuote.package_name}</strong>
              </div>
              <StatusBadge status={selectedQuote.status} />
            </div>

            <div className="border border-slate-200 rounded-lg overflow-hidden">
              <table className="w-full text-left">
                <thead className="bg-slate-100 text-slate-600 font-semibold">
                  <tr>
                    <th className="px-4 py-2">Item</th>
                    <th className="px-3 py-2">Quantity</th>
                    <th className="px-3 py-2">Unit Price</th>
                    <th className="px-4 py-2 text-right">Line Total</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200">
                  {selectedQuote.items.map((it, idx) => (
                    <tr key={idx} className="hover:bg-slate-50">
                      <td className="px-4 py-2 font-medium text-slate-800">{it.product_name}</td>
                      <td className="px-3 py-2 text-slate-700">{it.quantity}</td>
                      <td className="px-3 py-2 text-slate-700">₹{it.unit_price?.toLocaleString()}</td>
                      <td className="px-4 py-2 text-right font-semibold text-slate-900">₹{it.total_price?.toLocaleString()}</td>
                    </tr>
                  ))}
                </tbody>
                <tfoot className="bg-slate-50 border-t border-slate-200 font-semibold">
                  <tr>
                    <td colSpan={3} className="px-4 py-2 text-right text-slate-600">Subtotal:</td>
                    <td className="px-4 py-2 text-right">₹{selectedQuote.subtotal?.toLocaleString()}</td>
                  </tr>
                  <tr>
                    <td colSpan={3} className="px-4 py-1.5 text-right text-slate-600">GST (18%):</td>
                    <td className="px-4 py-1.5 text-right">₹{selectedQuote.tax?.toLocaleString()}</td>
                  </tr>
                  <tr className="text-sm font-bold text-amber-700 border-t border-slate-300">
                    <td colSpan={3} className="px-4 py-2 text-right">Total:</td>
                    <td className="px-4 py-2 text-right">₹{selectedQuote.total?.toLocaleString()}</td>
                  </tr>
                </tfoot>
              </table>
            </div>

            <div className="flex justify-between items-center pt-2">
              <button
                onClick={() => setSelectedQuote(null)}
                className="px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-100 transition"
              >
                Close
              </button>
              {selectedQuote.status === 'Draft' && (
                <button
                  onClick={() => {
                    handleConfirmAndCreateOrder(selectedQuote.id);
                    setSelectedQuote(null);
                  }}
                  className="px-4 py-2 bg-amber-500 hover:bg-amber-600 text-slate-950 font-semibold rounded-lg transition"
                >
                  Accept & Generate Sales Order
                </button>
              )}
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
