import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import StatusBadge from '../components/StatusBadge';
import { LoadingState, ErrorState, EmptyState } from '../components/States';

const rupees = (n) => `₹${Number(n || 0).toLocaleString('en-IN', { maximumFractionDigits: 0 })}`;
const showTime = (value) => (value ? new Date(`${value}Z`).toLocaleString('en-IN') : '');

export default function PortalSubsidy() {
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = async () => {
    try {
      setLoading(true);
      setError(null);
      setFiles(await api.getPortalSubsidies());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  if (loading) return <LoadingState message="Loading your subsidy file..." />;
  if (error) return <ErrorState title="Could not load your subsidy file" message={error} onRetry={load} />;
  if (files.length === 0) {
    return <EmptyState title="No subsidy file" description="If you asked for help with a government subsidy, its progress appears here once your order is confirmed." />;
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-bold text-slate-900">My subsidy</h2>
        <p className="text-xs text-slate-500">We handle the paperwork. Here is how far it has got.</p>
      </div>
      {files.map((file) => (
        <div key={file.id} className="bg-white rounded-xl border border-slate-200 p-5 space-y-3">
          <div className="flex items-center justify-between">
            <div>
              <div className="font-mono text-xs font-bold text-slate-700">{file.order_reference}</div>
              <h3 className="font-bold text-slate-900">{file.package_name}</h3>
            </div>
            <StatusBadge status={file.status} />
          </div>
          <dl className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
            <div><dt className="text-slate-500">Application number</dt><dd className="font-semibold">{file.reference_number || 'Not yet applied'}</dd></div>
            <div><dt className="text-slate-500">Expected</dt><dd className="font-semibold">{file.expected_amount ? rupees(file.expected_amount) : '-'}</dd></div>
            <div><dt className="text-slate-500">Received</dt><dd className="font-semibold">{file.received_amount ? rupees(file.received_amount) : '-'}</dd></div>
          </dl>
          <ol className="text-xs space-y-1">
            {file.steps.map((step, i) => (
              <li key={i} className="text-emerald-700">✓ {step.status} <span className="text-slate-400">{showTime(step.at)}</span></li>
            ))}
          </ol>
        </div>
      ))}
    </div>
  );
}
