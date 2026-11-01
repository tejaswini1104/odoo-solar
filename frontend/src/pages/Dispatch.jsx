import React, { useCallback, useEffect, useRef, useState } from 'react';
import { api } from '../api/client';
import DataTable from '../components/DataTable';
import StatusBadge from '../components/StatusBadge';
import Modal from '../components/Modal';
import { LoadingState, ErrorState } from '../components/States';
import { useToast } from '../components/Toast';
import { Truck, CheckCircle2, QrCode, Camera, X, ClipboardList } from 'lucide-react';
import CameraScanner from '../components/CameraScanner';
import ReplacementDispatch from '../components/ReplacementDispatch';
import { cameraScanSupported } from '../utils/cameraSupport';
import { serialFromScan } from '../utils/scanText';
import { useAuth } from '../auth/AuthContext';

export default function Dispatch({ setActiveTab }) {
  const { user } = useAuth();
  const isWarehouse = user?.role === 'warehouse'; // only the warehouse assigns serials and dispatches
  const [orders, setOrders] = useState([]);
  const [inventory, setInventory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeDispatchOrder, setActiveDispatchOrder] = useState(null);
  const [dispatchReqs, setDispatchReqs] = useState(null);
  const [assignedSerials, setAssignedSerials] = useState({});
  const [submittingDispatch, setSubmittingDispatch] = useState(false);
  const [pickList, setPickList] = useState(null);
  const [packed, setPacked] = useState({});
  const [scanText, setScanText] = useState('');
  const [cameraOpen, setCameraOpen] = useState(false);
  const scanBox = useRef(null);
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
      setScanText('');
      setCameraOpen(false);
      setPacked({});
      setAssignedSerials({}); // every serial number must be scanned, so nothing is filled in for the warehouse
      const [reqData, pick] = await Promise.all([api.getDispatchRequirements(order.id), api.getPickList(order.id)]);
      setDispatchReqs(reqData);
      setPickList(pick);
    } catch (err) {
      addToast(`Failed to load requirements: ${err.message}`, 'error');
    }
  };

  // One scan (handheld scanner, typed, or camera): put the serial in the right slot, or say why it cannot go there
  const acceptScan = useCallback((raw) => {
    const code = serialFromScan(raw).trim();
    if (!code || !dispatchReqs) return;
    const req = dispatchReqs.requirements.find((r) =>
      r.available_serials.some((sn) => sn.toLowerCase() === code.toLowerCase())
    );
    if (!req) {
      addToast(`"${code}" is not an in-stock serial number for the equipment on this order.`, 'error', 5000);
      return;
    }
    const exact = req.available_serials.find((sn) => sn.toLowerCase() === code.toLowerCase());
    const all = Object.values(assignedSerials).flat();
    if (all.includes(exact)) {
      addToast(`${exact} is already scanned.`, 'error', 4000);
      return;
    }
    const current = assignedSerials[req.product_id] || [];
    if (current.length >= req.required_quantity) {
      addToast(`${req.product_name}: all ${req.required_quantity} unit(s) are already scanned.`, 'error', 4000);
      return;
    }
    setAssignedSerials({ ...assignedSerials, [req.product_id]: [...current, exact] });
    addToast(`${exact} scanned for ${req.product_name}.`, 'success', 1500);
  }, [dispatchReqs, assignedSerials, addToast]);

  const removeScanned = (productId, serial) =>
    setAssignedSerials((prev) => ({ ...prev, [productId]: (prev[productId] || []).filter((sn) => sn !== serial) }));

  const allScanned = !!dispatchReqs && dispatchReqs.requirements.every(
    (r) => (assignedSerials[r.product_id] || []).length === r.required_quantity
  );

  const handleDelivered = async (order) => {
    try {
      await api.markDelivered(order.id);
      addToast('Delivery recorded. The warranty clock has started for every serial number and the panels.', 'success', 7000);
      loadData();
    } catch (err) {
      addToast(`Could not record delivery: ${err.message}`, 'error', 6000);
    }
  };

  const handleDispatch = async (e) => {
    e.preventDefault();
    if (!activeDispatchOrder) return;

    // Flatten all assigned serial numbers
    const serialList = Object.values(assignedSerials).flat().filter(Boolean);
    if (!allScanned) {
      addToast('Scan every serial number before dispatch.', 'error');
      return;
    }

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
          {row.status === 'Confirmed' && !isWarehouse ? (
            <span className="text-xs text-slate-500 font-medium">Warehouse dispatches</span>
          ) : row.status === 'Confirmed' ? (
            <button
              onClick={() => handleOpenDispatch(row)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold rounded-lg bg-purple-600 hover:bg-purple-700 text-white transition shadow-xs"
            >
              <Truck className="w-3.5 h-3.5" /> Assign Serials & Dispatch
            </button>
          ) : row.status === 'Dispatched' && !row.delivered_at && isWarehouse ? (
            <button
              onClick={() => handleDelivered(row)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-bold rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white transition shadow-xs"
              title="Confirm the goods have reached the customer. This starts the warranty."
            >
              <CheckCircle2 className="w-3.5 h-3.5" /> Mark delivered
            </button>
          ) : row.delivered_at ? (
            <span className="text-xs text-emerald-600 font-medium">
              ✓ Delivered {new Date(`${row.delivered_at}Z`).toLocaleDateString('en-IN')}
            </span>
          ) : (
            <span className="text-xs text-slate-500 font-medium">
              {row.status === 'Dispatched' ? 'Dispatched, awaiting delivery' : row.status === 'Completed' ? 'Dispatched' : 'Requires Confirmation'}
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

      <ReplacementDispatch />

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

            {pickList && (
              <div className="rounded-lg border border-slate-200">
                <div className="flex items-center gap-2 px-3 py-2 bg-slate-50 border-b border-slate-200 text-xs font-bold text-slate-800 uppercase tracking-wider">
                  <ClipboardList className="w-3.5 h-3.5" /> Pick list: pack everything
                </div>
                <div className="px-3 py-1.5 text-[11px] text-slate-500 border-b border-slate-100">
                  Deliver to {pickList.delivery_address}
                </div>
                <ul className="divide-y divide-slate-100 text-xs">
                  {pickList.lines.map((line) => (
                    <li key={line.product_id} className="flex items-center gap-3 px-3 py-2">
                      <input
                        type="checkbox"
                        checked={!!packed[line.product_id]}
                        onChange={(e) => setPacked({ ...packed, [line.product_id]: e.target.checked })}
                        className="w-4 h-4 rounded border-slate-300 text-emerald-600"
                        aria-label={`Packed ${line.product_name}`}
                      />
                      <div className="flex-1">
                        <span className={`font-semibold ${packed[line.product_id] ? 'line-through text-slate-400' : 'text-slate-900'}`}>{line.product_name}</span>
                        <span className="text-slate-500 ml-2">{line.category}</span>
                        {line.is_serialized && <span className="ml-2 text-purple-700 font-bold">needs serial</span>}
                      </div>
                      <span className="font-mono font-bold text-slate-800">{line.quantity} {line.unit}</span>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            <div className="space-y-3">
              <h5 className="text-xs font-bold text-slate-800 uppercase tracking-wider">
                Scan each serial number (mandatory):
              </h5>

              <div className="flex gap-2">
                <div className="relative flex-1">
                  <QrCode className="w-4 h-4 text-slate-400 absolute left-2.5 top-2.5" />
                  <input maxLength={100}
                    ref={scanBox}
                    autoFocus
                    value={scanText}
                    onChange={(e) => setScanText(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        e.preventDefault(); // a handheld scanner types the code and presses Enter
                        acceptScan(scanText);
                        setScanText('');
                      }
                    }}
                    placeholder="Scan or type a serial number, then press Enter"
                    className="w-full pl-8 pr-3 py-2 border border-slate-300 rounded-lg text-xs font-mono focus:ring-2 focus:ring-purple-500 focus:outline-none"
                  />
                </div>
                {cameraScanSupported() && (
                  <button
                    type="button"
                    onClick={() => setCameraOpen(!cameraOpen)}
                    className="inline-flex items-center gap-1.5 px-3 py-2 border border-slate-300 rounded-lg text-xs font-semibold text-slate-700 hover:bg-slate-100"
                  >
                    <Camera className="w-4 h-4" /> Camera
                  </button>
                )}
              </div>
              {cameraOpen && <CameraScanner onScan={acceptScan} onClose={() => setCameraOpen(false)} />}

              {dispatchReqs.requirements.map((req) => {
                const done = assignedSerials[req.product_id] || [];
                return (
                  <div key={req.product_id} className="p-3 bg-purple-50/60 rounded-lg border border-purple-200 text-xs">
                    <div className="flex justify-between items-center mb-2">
                      <span className="font-bold text-purple-900">{req.product_name}</span>
                      <span className={`px-2 py-0.5 rounded font-semibold ${done.length === req.required_quantity ? 'bg-emerald-200 text-emerald-900' : 'bg-purple-200 text-purple-900'}`}>
                        {done.length} of {req.required_quantity} scanned
                      </span>
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {done.map((sn) => (
                        <span key={sn} className="inline-flex items-center gap-1 px-2 py-1 bg-white border border-purple-200 rounded font-mono font-semibold text-slate-800">
                          {sn}
                          <button type="button" onClick={() => removeScanned(req.product_id, sn)} aria-label={`Remove ${sn}`}>
                            <X className="w-3 h-3 text-slate-400 hover:text-rose-600" />
                          </button>
                        </span>
                      ))}
                      {done.length === 0 && <span className="text-slate-500">Nothing scanned yet.</span>}
                    </div>
                  </div>
                );
              })}
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
                disabled={submittingDispatch || !allScanned}
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
