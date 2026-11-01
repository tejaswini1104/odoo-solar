import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import StatusBadge from '../components/StatusBadge';
import { LoadingState, ErrorState, EmptyState } from '../components/States';

// Times from the server are UTC without a zone marker. Add one so they show in the customer's own time.
const showTime = (value) => (value ? new Date(`${value}Z`).toLocaleString('en-IN') : null);
const showDate = (value) => (value ? new Date(value).toLocaleDateString('en-IN') : null);

export default function PortalInstallation() {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = async () => {
    try {
      setLoading(true);
      setError(null);
      setJobs(await api.getPortalInstallations());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  if (loading) return <LoadingState message="Loading your installation..." />;
  if (error) return <ErrorState title="Could not load your installation" message={error} onRetry={load} />;
  if (jobs.length === 0) {
    return <EmptyState title="No installation yet" description="Your installation job appears here once your order is confirmed." />;
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-lg font-bold text-slate-900">My installation</h2>
        <p className="text-xs text-slate-500">Progress, and the proof of the finished work.</p>
      </div>

      {jobs.map((job) => (
        <div key={job.id} className="bg-white rounded-xl border border-slate-200 p-5 space-y-4">
          <div className="flex items-center justify-between">
            <div>
              <div className="font-mono text-xs font-bold text-slate-700">{job.reference}</div>
              <h3 className="font-bold text-slate-900">{job.package_name}</h3>
            </div>
            <StatusBadge status={job.status} />
          </div>

          <ol className="text-xs space-y-1.5">
            <li className="text-emerald-700">✓ Order confirmed, installation scheduled for {showDate(job.scheduled_date)}</li>
            <li className={job.delivered_at ? 'text-emerald-700' : 'text-slate-400'}>
              {job.delivered_at ? `✓ Equipment delivered ${showTime(job.delivered_at)}. Your warranty has started.` : '○ Equipment delivery'}
            </li>
            <li className={job.start_time ? 'text-emerald-700' : 'text-slate-400'}>
              {job.start_time ? `✓ Work started ${showTime(job.start_time)}` : '○ Work started'}
            </li>
            <li className={job.finish_time ? 'text-emerald-700' : 'text-slate-400'}>
              {job.finish_time ? `✓ Work finished ${showTime(job.finish_time)}${job.confirmed_system_size ? `, ${job.confirmed_system_size} kW installed` : ''}` : '○ Work finished'}
            </li>
          </ol>

          {job.technician_name && (
            <p className="text-xs text-slate-600">Technician: <strong>{job.technician_name}</strong></p>
          )}

          {job.photos.length > 0 && (
            <div>
              <h4 className="text-xs font-bold text-slate-900 mb-2">Photos of the finished roof</h4>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                {job.photos.map((p) => (
                  <a key={p.id} href={p.url} target="_blank" rel="noreferrer">
                    <img src={p.url} alt={p.caption || 'Finished roof'} className="w-full h-32 object-cover rounded-lg border border-slate-200" />
                  </a>
                ))}
              </div>
            </div>
          )}

          {job.signature_url && (
            <div>
              <h4 className="text-xs font-bold text-slate-900 mb-2">Your acceptance</h4>
              <img src={job.signature_url} alt="Your signature" className="h-20 border border-slate-200 rounded-lg bg-white" />
              <p className="text-xs text-slate-600 mt-1">
                Signed by <strong>{job.signed_by_name}</strong> on {showTime(job.signed_at)}
              </p>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
