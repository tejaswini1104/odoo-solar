import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import StatusBadge from './StatusBadge';
import { useToast } from './Toast';
import { useAuth } from '../auth/AuthContext';
import { LifeBuoy } from 'lucide-react';

// Replacement units for approved repair tickets. Support only asks; the warehouse picks the serial and sends it.
export default function ReplacementDispatch() {
  const { user } = useAuth();
  const canSend = user?.role === 'warehouse';
  const [requests, setRequests] = useState([]);
  const [chosen, setChosen] = useState({});
  const [busy, setBusy] = useState(null);
  const [error, setError] = useState(null);
  const { addToast } = useToast();

  const load = async () => {
    try {
      setError(null);
      setRequests(await api.getReplacementRequests());
    } catch (err) {
      setError(err.message);
    }
  };

  useEffect(() => {
    load();
  }, []);

  const send = async (req) => {
    try {
      setBusy(req.ticket_id);
      await api.sendReplacement(req.ticket_id, chosen[req.ticket_id]);
      addToast(`Replacement for ${req.reference} dispatched. Stock has been reduced.`, 'success');
      load();
    } catch (err) {
      addToast(`Error: ${err.message}`, 'error', 6000);
    } finally {
      setBusy(null);
    }
  };

  const waiting = requests.filter((r) => r.status === 'Awaiting Dispatch');
  const sent = requests.filter((r) => r.status === 'Dispatched');

  return (
    <div className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs space-y-4">
      <div className="flex items-center gap-2">
        <LifeBuoy className="w-5 h-5 text-purple-600" />
        <div>
          <h4 className="text-base font-bold text-slate-900">Replacement Units for Repairs</h4>
          <p className="text-xs text-slate-500">
            Approved repair tickets that need a new unit. Pick an in-stock serial of the same product and send it. The technician fits it on site.
          </p>
        </div>
      </div>

      {error && <p className="text-xs text-rose-700">{error}</p>}
      {!error && waiting.length === 0 && <p className="text-xs text-slate-500">No replacements waiting to be sent.</p>}

      {waiting.map((req) => (
        <div key={req.ticket_id} className="border border-slate-200 rounded-lg p-3 text-xs flex flex-col md:flex-row md:items-center gap-3 justify-between">
          <div className="space-y-0.5">
            <div>
              <span className="font-mono font-bold text-slate-800">{req.reference}</span>{' '}
              <StatusBadge status={req.status} />
            </div>
            <div className="font-semibold text-slate-900">{req.customer_name}</div>
            <div className="text-slate-500">{req.delivery_address}</div>
            <div className="text-slate-600">
              {req.is_panel ? 'One solar panel (no serial number)' : <>Replaces <span className="font-mono font-semibold">{req.faulty_serial}</span> · {req.product_name}</>}
            </div>
            {req.technician_name && <div className="text-slate-500">Technician: {req.technician_name}</div>}
          </div>

          {canSend ? (
            <div className="flex items-center gap-2">
              {!req.is_panel && (
                <select
                  value={chosen[req.ticket_id] || ''}
                  onChange={(e) => setChosen({ ...chosen, [req.ticket_id]: e.target.value })}
                  className="px-2 py-1.5 border border-slate-300 rounded-lg bg-white font-mono focus:ring-2 focus:ring-amber-500 focus:outline-none"
                >
                  <option value="">{req.available_serials.length ? 'Choose a serial' : 'None in stock'}</option>
                  {req.available_serials.map((s) => <option key={s} value={s}>{s}</option>)}
                </select>
              )}
              <button
                onClick={() => send(req)}
                disabled={busy === req.ticket_id || (!req.is_panel && !chosen[req.ticket_id])}
                className="px-3 py-1.5 font-semibold rounded-lg bg-purple-600 hover:bg-purple-700 text-white transition disabled:opacity-50"
              >
                Dispatch
              </button>
            </div>
          ) : (
            <span className="text-slate-400">Sent by the warehouse</span>
          )}
        </div>
      ))}

      {sent.length > 0 && (
        <div className="text-xs text-slate-500 border-t border-slate-100 pt-3">
          Sent, waiting to be fitted:{' '}
          {sent.map((r) => (
            <span key={r.ticket_id} className="inline-block mr-3">
              <span className="font-mono font-semibold text-slate-700">{r.reference}</span>
              {r.dispatch_serial ? ` (${r.dispatch_serial})` : ' (panel)'}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
