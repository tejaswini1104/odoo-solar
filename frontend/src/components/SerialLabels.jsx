import React, { useEffect, useState } from 'react';
import { Printer, QrCode } from 'lucide-react';
import { api } from '../api/client';
import { useToast } from './Toast';

const qrUrl = (serial) => `${window.location.origin}/api/stock/qr.png?serial=${encodeURIComponent(serial)}`;
const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

// A sheet of QR labels, one per serial-numbered unit. Scanning a label fills the serial number at dispatch and in
// Support, and a phone camera that scans it opens the public warranty check.
export default function SerialLabels() {
  const { addToast } = useToast();
  const [status, setStatus] = useState('In Stock');
  const [units, setUnits] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let current = true;
    setLoading(true);
    api.getStockSerials(status)
      .then((rows) => { if (current) setUnits(rows); })
      .catch((err) => addToast(`Could not load the serial numbers: ${err.message}`, 'error'))
      .finally(() => { if (current) setLoading(false); });
    return () => { current = false; };
  }, [status]);

  const print = () => {
    const win = window.open('', '_blank', 'width=900,height=1000');
    if (!win) {
      window.alert('Allow pop-ups for this site to print the labels.');
      return;
    }
    const cells = units.map((u) => `
      <div class="label">
        <img src="${esc(qrUrl(u.serial_number))}" alt="">
        <div class="serial">${esc(u.serial_number)}</div>
        <div class="name">${esc(u.product_name)}</div>
      </div>`).join('');
    win.document.write(`<!doctype html><html><head><meta charset="utf-8"><title>Serial number labels</title><style>
      body { font-family: Arial, sans-serif; margin: 12mm; }
      .grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8mm; }
      .label { border: 1px dashed #94a3b8; padding: 4mm; text-align: center; break-inside: avoid; }
      .label img { width: 32mm; height: 32mm; }
      .serial { font: bold 11px monospace; margin-top: 2mm; }
      .name { font-size: 9px; color: #475569; margin-top: 1mm; }
    </style></head><body><div class="grid">${cells}</div></body></html>`);
    win.document.close();
    win.focus();
    // Wait for the QR images before the print dialog opens
    const images = Array.from(win.document.images);
    Promise.all(images.map((img) => (img.complete ? null : new Promise((done) => { img.onload = done; img.onerror = done; }))))
      .then(() => win.print());
  };

  return (
    <div className="space-y-3">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
        <div>
          <h3 className="text-lg font-bold text-slate-900 flex items-center gap-2"><QrCode className="w-5 h-5" /> QR labels for serial numbers</h3>
          <p className="text-xs text-slate-500">Stick one on each unit. Scanning it fills the serial number at dispatch and in Support, and opens the warranty check on a phone.</p>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value)}
            className="px-2 py-1.5 border border-slate-300 rounded-lg text-xs bg-white"
          >
            <option value="In Stock">In stock</option>
            <option value="Dispatched">Dispatched</option>
            <option value="Installed">Installed</option>
            <option value="all">All units</option>
          </select>
          <button
            type="button"
            onClick={print}
            disabled={loading || units.length === 0}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-slate-900 text-white rounded-lg text-xs font-semibold hover:bg-slate-700 disabled:opacity-50"
          >
            <Printer className="w-4 h-4" /> Print labels
          </button>
        </div>
      </div>

      {loading ? (
        <p className="text-xs text-slate-500">Loading...</p>
      ) : units.length === 0 ? (
        <p className="text-xs text-slate-500">No units with this status.</p>
      ) : (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
          {units.map((u) => (
            <div key={u.serial_number} className="border border-slate-200 rounded-lg p-2 text-center bg-white">
              <img src={qrUrl(u.serial_number)} alt={`QR code for ${u.serial_number}`} className="w-28 h-28 mx-auto" loading="lazy" />
              <div className="font-mono text-[11px] font-bold text-slate-800 mt-1 break-all">{u.serial_number}</div>
              <div className="text-[10px] text-slate-500">{u.product_name}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
