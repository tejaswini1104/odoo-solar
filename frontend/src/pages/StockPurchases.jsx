import React, { useEffect, useState } from 'react';
import { Plus, Trash2, Download } from 'lucide-react';
import { api } from '../api/client';
import { useAuth } from '../auth/AuthContext';
import DataTable from '../components/DataTable';
import Modal from '../components/Modal';
import { LoadingState, ErrorState } from '../components/States';
import { useToast } from '../components/Toast';
import { localIsoDate } from '../utils/dates';

const rupees = (n) => `₹${Number(n || 0).toLocaleString('en-IN', { maximumFractionDigits: 2 })}`;
const todayIso = () => localIsoDate();
const emptyLine = () => ({ product_id: '', quantity: '1', unit_cost: '', serials: '' });
const serialList = (text) => text.split(/[\n,;]+/).map((s) => s.trim()).filter(Boolean);

// Stock bought from suppliers. Bulk items raise the quantity; serialized items need one serial number per unit.
export default function StockPurchases() {
  const { user } = useAuth();
  const canReceive = user?.role === 'warehouse';
  const { addToast } = useToast();
  const [products, setProducts] = useState([]);
  const [purchases, setPurchases] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState(null);
  const [supplier, setSupplier] = useState('');
  const [invoiceRef, setInvoiceRef] = useState('');
  const [date, setDate] = useState(todayIso());
  const [lines, setLines] = useState([emptyLine()]);

  const load = async () => {
    try {
      setLoading(true);
      setError(null);
      const [productData, purchaseData] = await Promise.all([api.getStockProducts(), api.getStockPurchases()]);
      setProducts(productData);
      setPurchases(purchaseData);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const productOf = (id) => products.find((p) => String(p.id) === String(id));
  const updateLine = (index, patch) => setLines(lines.map((l, i) => (i === index ? { ...l, ...patch } : l)));

  const reset = () => {
    setSupplier('');
    setInvoiceRef('');
    setDate(todayIso());
    setLines([emptyLine()]);
    setFormError(null);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setFormError(null);
    try {
      setSaving(true);
      await api.receiveStock({
        supplier,
        invoice_reference: invoiceRef || null,
        purchased_on: date,
        items: lines.map((l) => ({
          product_id: Number(l.product_id),
          quantity: Number(l.quantity),
          unit_cost: Number(l.unit_cost),
          serial_numbers: productOf(l.product_id)?.is_serialized ? serialList(l.serials) : [],
        })),
      });
      addToast('Stock received and added to the warehouse.', 'success');
      setOpen(false);
      reset();
      load();
    } catch (err) {
      setFormError(err.message);
    } finally {
      setSaving(false);
    }
  };

  if (loading) return <LoadingState message="Loading stock purchases..." />;
  if (error) return <ErrorState title="Could not load stock purchases" message={error} onRetry={load} />;

  const columns = [
    {
      header: 'Purchase',
      accessor: 'supplier',
      render: (row) => (
        <div className="text-xs">
          <div className="font-semibold text-slate-900">{row.supplier}</div>
          <div className="text-slate-500">{new Date(row.purchased_on).toLocaleDateString('en-IN')}{row.invoice_reference ? ` · ${row.invoice_reference}` : ''}</div>
        </div>
      )
    },
    {
      header: 'Items received',
      accessor: 'items',
      render: (row) => (
        <ul className="text-xs space-y-0.5">
          {row.items.map((item, idx) => (
            <li key={idx}>
              <span className="font-medium text-slate-800">{item.quantity} × {item.product_name}</span>
              <span className="text-slate-500"> at {rupees(item.unit_cost)}</span>
            </li>
          ))}
        </ul>
      )
    },
    {
      header: 'Total cost',
      accessor: 'total_cost',
      render: (row) => <span className="text-xs font-bold text-slate-900">{rupees(row.total_cost)}</span>
    },
  ];

  const field = 'w-full px-3 py-2 border border-slate-300 rounded-lg bg-white focus:ring-2 focus:ring-amber-500 focus:outline-none';
  const label = 'block text-xs font-semibold text-slate-700 mb-1';

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
        <div>
          <h3 className="text-lg font-bold text-slate-900">Stock purchases</h3>
          <p className="text-xs text-slate-500">
            What was bought from suppliers and what it cost. Receiving stock adds it to the warehouse, and every serialized unit goes into the serial register.
          </p>
        </div>
        <div className="flex gap-2">
          <a
            href="/api/stock/purchases.csv"
            className="inline-flex items-center gap-1.5 px-3 py-2 border border-slate-300 rounded-lg text-xs font-semibold text-slate-700 hover:bg-slate-100 transition"
          >
            <Download className="w-3.5 h-3.5" /> Download
          </a>
          {canReceive && (
            <button
              onClick={() => setOpen(true)}
              className="inline-flex items-center gap-2 px-3.5 py-2 bg-amber-500 hover:bg-amber-600 text-slate-950 rounded-lg text-sm font-semibold shadow-xs transition"
            >
              <Plus className="w-4 h-4" /> Receive stock
            </button>
          )}
        </div>
      </div>

      <DataTable columns={columns} data={purchases} searchPlaceholder="Search by supplier or product..." emptyTitle="No purchases recorded yet" emptyDescription="Stock you receive from suppliers appears here." />

      <Modal isOpen={open} onClose={() => { setOpen(false); reset(); }} title="Receive stock from a supplier" maxWidth="max-w-3xl">
        <form onSubmit={handleSubmit} className="space-y-4 text-sm">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div>
              <label className={label}>Supplier</label>
              <input maxLength={255} required minLength={2} value={supplier} onChange={(e) => setSupplier(e.target.value)} className={field} />
            </div>
            <div>
              <label className={label}>Supplier invoice or delivery note</label>
              <input maxLength={100} value={invoiceRef} onChange={(e) => setInvoiceRef(e.target.value)} className={field} />
            </div>
            <div>
              <label className={label}>Purchase date</label>
              <input required type="date" max={todayIso()} value={date} onChange={(e) => setDate(e.target.value)} className={field} />
            </div>
          </div>

          <div className="space-y-3">
            {lines.map((line, index) => {
              const product = productOf(line.product_id);
              const serials = serialList(line.serials);
              const needed = Number(line.quantity) || 0;
              return (
                <div key={index} className="border border-slate-200 rounded-lg p-3 space-y-2 bg-slate-50">
                  <div className="grid grid-cols-1 sm:grid-cols-12 gap-2 items-end">
                    <div className="sm:col-span-6">
                      <label className={label}>Product</label>
                      <select required value={line.product_id} onChange={(e) => updateLine(index, { product_id: e.target.value, serials: '' })} className={field}>
                        <option value="">Choose a product</option>
                        {products.map((p) => (
                          <option key={p.id} value={p.id}>{p.name}{p.is_serialized ? ' (serial numbers)' : ''}</option>
                        ))}
                      </select>
                    </div>
                    <div className="sm:col-span-2">
                      <label className={label}>Quantity</label>
                      <input max="1000" required type="number" min="1" value={line.quantity} onChange={(e) => updateLine(index, { quantity: e.target.value })} className={field} />
                    </div>
                    <div className="sm:col-span-3">
                      <label className={label}>Cost each (₹)</label>
                      <input max="10000000" required type="number" min="0" step="0.01" value={line.unit_cost} onChange={(e) => updateLine(index, { unit_cost: e.target.value })} className={field} />
                    </div>
                    <div className="sm:col-span-1 flex sm:justify-end">
                      {lines.length > 1 && (
                        <button type="button" onClick={() => setLines(lines.filter((_, i) => i !== index))} className="p-2 text-slate-400 hover:text-rose-600" title="Remove this line">
                          <Trash2 className="w-4 h-4" />
                        </button>
                      )}
                    </div>
                  </div>
                  {product?.is_serialized && (
                    <div>
                      <label className={label}>Serial numbers, one per line ({serials.length} of {needed} entered)</label>
                      <textarea maxLength={5000}
                        rows={Math.min(Math.max(needed, 2), 6)}
                        value={line.serials}
                        onChange={(e) => updateLine(index, { serials: e.target.value })}
                        placeholder="Scan each unit, or type the serial numbers"
                        className={`${field} font-mono text-xs ${serials.length === needed ? '' : 'border-amber-400'}`}
                      />
                    </div>
                  )}
                </div>
              );
            })}
            <button type="button" onClick={() => setLines([...lines, emptyLine()])} className="text-xs font-semibold text-amber-700 hover:text-amber-800">
              + Add another product
            </button>
          </div>

          {formError && <div className="text-xs text-rose-700 bg-rose-50 border border-rose-200 rounded-lg p-2.5">{formError}</div>}

          <div className="flex justify-end gap-3 pt-3 border-t border-slate-200">
            <button type="button" onClick={() => { setOpen(false); reset(); }} className="px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-100 transition text-xs">Cancel</button>
            <button type="submit" disabled={saving} className="px-4 py-2 bg-amber-500 hover:bg-amber-600 text-slate-950 font-semibold rounded-lg transition text-xs disabled:opacity-50">
              {saving ? 'Saving...' : 'Receive stock'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
