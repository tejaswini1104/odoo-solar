import React, { useEffect, useState } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { ShieldCheck, ShieldAlert, Clock, Repeat, Search } from 'lucide-react';

const STATES = {
  active: { icon: ShieldCheck, tone: 'border-emerald-300 bg-emerald-50 text-emerald-800', title: 'Under warranty' },
  expired: { icon: ShieldAlert, tone: 'border-rose-300 bg-rose-50 text-rose-800', title: 'Warranty ended' },
  not_started: { icon: Clock, tone: 'border-amber-300 bg-amber-50 text-amber-800', title: 'Warranty not started yet' },
  replaced: { icon: Repeat, tone: 'border-slate-300 bg-slate-50 text-slate-700', title: 'Unit replaced' },
};

const day = (value) => new Date(value).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });

// The page a phone opens after scanning the QR label on a unit. No sign-in, and it never shows who owns the unit.
export default function WarrantyCheck() {
  const [params, setParams] = useSearchParams();
  const serial = (params.get('serial') || '').trim();
  const [typed, setTyped] = useState(serial);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setResult(null);
    setError(null);
    if (serial.length < 3) return undefined;
    let current = true;
    setLoading(true);
    fetch(`/api/public/warranty?serial=${encodeURIComponent(serial)}`)
      .then(async (res) => {
        const body = await res.json().catch(() => ({}));
        if (!res.ok) throw new Error(body.detail || 'Could not check this serial number.');
        return body;
      })
      .then((body) => { if (current) setResult(body); })
      .catch((err) => { if (current) setError(err.message); })
      .finally(() => { if (current) setLoading(false); });
    return () => { current = false; };
  }, [serial]);

  const state = result ? STATES[result.state] : null;
  const Icon = state?.icon;

  return (
    <div className="min-h-screen bg-slate-100 flex items-start justify-center p-4">
      <div className="w-full max-w-md mt-8 space-y-4">
        <div className="text-center">
          <div className="text-xl font-bold text-slate-900">SunPower Solutions</div>
          <div className="text-xs text-slate-500">Warranty check</div>
        </div>

        <form
          onSubmit={(e) => { e.preventDefault(); setParams(typed.trim() ? { serial: typed.trim() } : {}); }}
          className="flex gap-2"
        >
          <input
            value={typed}
            onChange={(e) => setTyped(e.target.value)}
            placeholder="Serial number, for example INV-2026-0042"
            className="flex-1 px-3 py-2 border border-slate-300 rounded-lg text-sm font-mono bg-white focus:ring-2 focus:ring-amber-500 focus:outline-none"
          />
          <button type="submit" className="inline-flex items-center gap-1 px-3 py-2 bg-amber-500 hover:bg-amber-600 text-slate-950 rounded-lg text-sm font-semibold">
            <Search className="w-4 h-4" /> Check
          </button>
        </form>

        {loading && <p className="text-sm text-slate-500 text-center">Checking...</p>}
        {error && <div className="rounded-lg border border-rose-300 bg-rose-50 text-rose-800 text-sm p-4">{error}</div>}

        {result && state && (
          <div className={`rounded-xl border p-5 space-y-3 ${state.tone}`}>
            <div className="flex items-center gap-2 text-lg font-bold"><Icon className="w-6 h-6" /> {state.title}</div>
            <div>
              <div className="text-sm font-semibold">{result.product_name}</div>
              <div className="font-mono text-xs">{result.serial_number}</div>
            </div>
            {result.end_date && (
              <dl className="grid grid-cols-2 gap-2 text-xs">
                <div><dt className="opacity-70">Started</dt><dd className="font-semibold">{day(result.start_date)}</dd></div>
                <div><dt className="opacity-70">{result.state === 'active' ? 'Ends' : 'Ended'}</dt><dd className="font-semibold">{day(result.end_date)}</dd></div>
                {result.state === 'active' && (
                  <div className="col-span-2"><dt className="opacity-70">Time left</dt><dd className="font-semibold">{result.days_left.toLocaleString('en-IN')} days</dd></div>
                )}
              </dl>
            )}
            <p className="text-sm">{result.message}</p>
          </div>
        )}

        <p className="text-center text-xs text-slate-500">
          Need a repair? Sign in to raise a ticket from your <Link to="/login" className="underline">customer account</Link>.
        </p>
      </div>
    </div>
  );
}
