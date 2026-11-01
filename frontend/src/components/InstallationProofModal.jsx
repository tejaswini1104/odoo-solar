import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import Modal from './Modal';

// Utc timestamps from the server carry no zone marker, so add one before showing them in local time
const showTime = (value) => (value ? new Date(`${value}Z`).toLocaleString('en-IN') : '-');

// The record of a finished job: when it was done, the photos, and the homeowner's signature.
export default function InstallationProofModal({ installation, onClose }) {
  const [photos, setPhotos] = useState([]);

  useEffect(() => {
    if (installation) api.getInstallationPhotos(installation.id).then(setPhotos).catch(() => setPhotos([]));
  }, [installation]);

  return (
    <Modal
      isOpen={Boolean(installation)}
      onClose={onClose}
      title={installation ? `Proof of work: JOB-${String(installation.id).padStart(4, '0')}` : 'Proof of work'}
      maxWidth="max-w-2xl"
    >
      {installation && (
        <div className="space-y-4 text-sm">
          <dl className="grid grid-cols-2 gap-x-6 gap-y-1 text-xs bg-slate-50 border border-slate-200 rounded-lg p-3">
            <dt className="text-slate-500">Customer</dt><dd className="font-semibold text-slate-900">{installation.customer_name}</dd>
            <dt className="text-slate-500">Technician</dt><dd className="font-semibold text-slate-900">{installation.technician_name}</dd>
            <dt className="text-slate-500">Started</dt><dd>{showTime(installation.start_time)}</dd>
            <dt className="text-slate-500">Finished</dt><dd>{showTime(installation.finish_time)}</dd>
            <dt className="text-slate-500">Installed size</dt><dd>{installation.confirmed_system_size} kW</dd>
          </dl>

          <div>
            <h4 className="text-xs font-bold text-slate-900 mb-2">Photos ({photos.length})</h4>
            {photos.length === 0 ? (
              <p className="text-xs text-slate-500">No photos were recorded for this job.</p>
            ) : (
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                {photos.map((p) => (
                  <a key={p.id} href={p.url} target="_blank" rel="noreferrer">
                    <img src={p.url} alt={p.caption || 'Finished roof'} className="w-full h-32 object-cover rounded-lg border border-slate-200" />
                  </a>
                ))}
              </div>
            )}
          </div>

          <div>
            <h4 className="text-xs font-bold text-slate-900 mb-2">Homeowner's acceptance</h4>
            {installation.signed_by_name ? (
              <div className="border border-slate-200 rounded-lg p-3">
                <img
                  src={`/api/installations/${installation.id}/signature/file`}
                  alt="Homeowner's signature"
                  className="h-24 bg-white"
                />
                <p className="text-xs text-slate-600 mt-1">
                  Signed by <strong>{installation.signed_by_name}</strong> on {showTime(installation.signed_at)}
                </p>
              </div>
            ) : (
              <p className="text-xs text-slate-500">No signature was recorded for this job.</p>
            )}
          </div>
        </div>
      )}
    </Modal>
  );
}
