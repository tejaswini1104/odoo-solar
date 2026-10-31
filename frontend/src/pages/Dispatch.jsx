import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import DataTable from '../components/DataTable';
import StatusBadge from '../components/StatusBadge';
import Modal from '../components/Modal';
import { LoadingState, ErrorState } from '../components/States';
import { useToast } from '../components/Toast';
import { Truck, Box, ShieldCheck, AlertCircle, CheckCircle2, QrCode } from 'lucide-react';

export default function Dispatch({ setActiveTab }) {
  const [orders, setOrders] = useState([]);
  const [inventory, setInventory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeDispatchOrder, setActiveDispatchOrder] = useState(null);
  const [dispatchReqs, setDispatchReqs] = useState(null);
  const [assignedSerials, setAssignedSerials] = useState({});
  const [submittingDispatch, setSubmittingDispatch] = useState(false);
  const { addToast } = useToast();

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [allOrders, invData] = await Promise.all([
        api.getOrders(),
        api.getInventory()
      ]);
      setOrders(allOrders);
      setInventory(invData);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleOpenDispatch = async (order) => {
    try {
      setActiveDispatchOrder(order);
      const reqData = await api.getDispatchRequirements(order.id);
      setDispatchReqs(reqData);

      // Pre-fill initial assigned serials if available
      const initialAssigned = {};
      reqData.requirements.forEach((req) => {
        initialAssigned[req.product_id] = req.available_serials.slice(0, req.required_quantity);
      });
      setAssignedSerials(initialAssigned);
    } catch (err) {
      addToast(`Failed to load requirements: ${err.message}`, 'error');
    }
  };

  const handleDispatch = async (e) => {
    e.preventDefault();
    if (!activeDispatchOrder) return;

    // Flatten all assigned serial numbers
    const serialList = Object.values(assignedSerials).flat().filter(Boolean);

    try {
      setSubmittingDispatch(true);
      await api.dispatchSerials(activeDispatchOrder.id, serialList);
      addToast(
        `Order SO-${activeDispatchOrder.id.toString().padStart(4, '0')} dispatched successfully! Inventory updated and serials validated.`,
        'success'
      );
      setActiveDispatchOrder(null);
      loadData();
      if (setActiveTab) setActiveTab('installations');
    } catch (err) {
      addToast(`Dispatch Failed: ${err.message}`, 'error', 6000);
    } finally {
      setSubmittingDispatch(false);
    }
  };

  const orderColumns = [
    {
      header: 'Order ID & Customer',
      accessor: 'id',
      render: (row) => (
        <div>
          <span className="font-mono text-xs font-bold text-slate-800">SO-{row.id.toString().padStart(4, '0')}</span>
          <div className="font-semibold text-slate-900 mt-0.5">{row.customer_name}</div>
        </div>
      )
    },
    {
      header: 'Solar Package',
      accessor: 'package_name',
      render: (row) => <span className="text-xs font-medium text-slate-800">{row.package_name}</span>
    },
    {
      header: 'Dispatch Readiness',
      accessor: 'status',
      render: (row) => {
        if (row.status === 'Confirmed') {
          return (
            <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
              <CheckCircle2 className="w-3.5 h-3.5" /> Ready to Dispatch
            </span>
          );
        }
        return <StatusBadge status={row.status} />;
      }
    },
    {
      header: 'Actions',
      accessor: 'id',
      render: (row) => (
        <div>
          {row.status === 'Confirmed' ? (
            <button
              onClick={() => handleOpenDispatch(row)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold rounded-lg bg-purple-600 hover:bg-purple-700 text-white transition shadow-xs"
            >
              <Truck className="w-3.5 h-3.5" /> Assign Serials & Dispatch
            </button>
          ) : (
            <span className="text-xs text-slate-500 font-medium">
              {row.status === 'Dispatched' || row.status === 'Completed' ? 'Dispatched' : 'Requires Confirmation'}
            </span>
          )}
        </div>
      )
    }
  ];

  if (loading) return <LoadingState message="Loading warehouse dispatch & inventory..." />;
  if (error) return <ErrorState title="Failed to load dispatch" message={error} onRetry={loadData} />;

  return (
    <div className="space-y-6">
      {/* Policy Banner */}
      <div className="bg-purple-50 border border-purple-200 rounded-xl p-3.5 text-xs text-purple-950 flex items-start gap-3">
        <QrCode className="w-5 h-5 text-purple-600 shrink-0 mt-0.5" />
        <div>
          <strong>STRICT SERIAL NUMBER VALIDATION BEFORE DISPATCH:</strong> Inverters, Batteries, and Charge
          Controllers must have unique, in-stock serial numbers scanned/entered before the truck leaves the warehouse.
          The backend enforces DB-level unique constraints and rejects dispatch if any serialized item is missing.
        </div>
      </div>

      <div>
        <h3 className="text-lg font-bold text-slate-900">Orders Ready for Warehouse Fulfillment</h3>
        <p className="text-xs text-slate-500">Assign verified hardware serial numbers to confirmed customer installations.</p>
      </div>

      <DataTable
        columns={orderColumns}
        data={orders}
        searchPlaceholder="Search orders to dispatch..."
      />

      {/* Stock Level Overview */}
      <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h4 className="text-base font-bold text-slate-900">Warehouse Stock Status (Live Inventory)</h4>
            <p className="text-xs text-slate-500">Bulk inventory quantities and serialized tracking counts.</p>
          </div>
          <span className="text-xs font-semibold px-2.5 py-1 bg-slate-100 rounded text-slate-700">
            {inventory.length} SKUs Tracked
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {inventory.map((item) => (
            <div key={item.id} className="p-3 bg-slate-50 rounded-lg border border-slate-200 text-xs">
              <div className="font-bold text-slate-800 truncate mb-1">{item.product_name}</div>
              <div className="text-[11px] text-slate-500 mb-2">
                Category: {item.category} {item.is_serialized && <span className="text-purple-600 font-bold">• Serialized</span>}
              </div>
              <div className="grid grid-cols-3 gap-1 text-center bg-white p-1.5 rounded border border-slate-200">
                <div>
                  <div className="text-slate-400 text-[10px]">On Hand</div>
                  <div className="font-bold text-slate-800">{item.quantity_on_hand}</div>
                </div>
                <div>
                  <div className="text-amber-500 text-[10px]">Reserved</div>
                  <div className="font-bold text-amber-700">{item.reserved_quantity}</div>
                </div>
                <div>
                  <div className="text-emerald-500 text-[10px]">Available</div>
                  <div className="font-bold text-emerald-700">{item.available_quantity}</div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Serial Assignment Modal */}
      <Modal
        isOpen={!!activeDispatchOrder && !!dispatchReqs}
        onClose={() => setActiveDispatchOrder(null)}
        title={activeDispatchOrder ? `Dispatch Order SO-${activeDispatchOrder.id.toString().padStart(4, '0')}` : 'Dispatch'}
        maxWidth="max-w-2xl"
      >
        {activeDispatchOrder && dispatchReqs && (
          <form onSubmit={handleDispatch} className="space-y-4 text-sm">
            <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 text-xs">
              <div className="font-semibold text-slate-900">{dispatchReqs.package_name}</div>
              <div className="text-slate-500 mt-0.5">Customer: {activeDispatchOrder.customer_name}</div>
            </div>

            <div className="space-y-3">
              <h5 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                Serialized Hardware Assignment (Mandatory):
              </h5>

              {dispatchReqs.requirements.map((req) => (
                <div key={req.product_id} className="p-3 bg-purple-50/60 rounded-lg border border-purple-200 text-xs">
                  <div className="flex justify-between items-center mb-2">
                    <span className="font-bold text-purple-900">{req.product_name}</span>
                    <span className="px-2 py-0.5 rounded bg-purple-200 text-purple-900 font-semibold">
                      Requires {req.required_quantity} Serial Number(s)
                    </span>
                  </div>

                  {Array.from({ length: req.required_quantity }).map((_, idx) => (
                    <div key={idx} className="mt-2">
                      <label className="block text-[11px] font-semibold text-slate-700 mb-1">
                        Unit #{idx + 1} Serial Number *
                      </label>
                      <div className="flex gap-2">
                        <select
                          required
                          value={assignedSerials[req.product_id]?.[idx] || ''}
                          onChange={(e) => {
                            const val = e.target.value;
                            setAssignedSerials((prev) => {
                              const curr = [...(prev[req.product_id] || [])];
                              curr[idx] = val;
                              return { ...prev, [req.product_id]: curr };
                            });
                          }}
                          className="w-full px-3 py-1.5 border border-slate-300 rounded-lg bg-white text-xs font-mono font-medium focus:ring-2 focus:ring-purple-500"
                        >
                          <option value="">-- Select In-Stock Serial Number --</option>
                          {req.available_serials.map((s) => (
                            <option key={s} value={s}>
                              {s} (In Stock)
                            </option>
                          ))}
                        </select>
                      </div>
                    </div>
                  ))}
                </div>
              ))}
            </div>

            <div className="flex justify-end gap-3 pt-4 border-t border-slate-200">
              <button
                type="button"
                onClick={() => setActiveDispatchOrder(null)}
                className="px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-100 transition"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={submittingDispatch}
                className="px-4 py-2 bg-purple-600 hover:bg-purple-700 text-white font-semibold rounded-lg transition disabled:opacity-50 flex items-center gap-2"
              >
                <Truck className="w-4 h-4" />
                {submittingDispatch ? 'Verifying & Dispatching...' : 'Confirm Dispatch & Deduct Stock'}
              </button>
            </div>
          </form>
        )}
      </Modal>
    </div>
  );
}
