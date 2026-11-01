import React, { useCallback, useEffect, useState } from 'react';
import { CheckCircle2, Camera, X } from 'lucide-react';
import { api } from '../api/client';
import Modal from './Modal';
import SignaturePad from './SignaturePad';
import { useToast } from './Toast';

// datetime-local wants "YYYY-MM-DDTHH:mm" in the person's own time zone
const toLocalInput = (date) => {
  const pad = (n) => String(n).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
};

// Phone photos are large. Shrink them before sending so uploads work on a poor connection.
async function shrinkPhoto(file, maxSide = 1600) {
  try {
    const bitmap = await createImageBitmap(file);
    const scale = Math.min(1, maxSide / Math.max(bitmap.width, bitmap.height));
    if (scale === 1 && file.size < 2 * 1024 * 1024) return file;
    const canvas = document.createElement('canvas');
    canvas.width = Math.round(bitmap.width * scale);
    canvas.height = Math.round(bitmap.height * scale);
    canvas.getContext('2d').drawImage(bitmap, 0, 0, canvas.width, canvas.height);
    const blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/jpeg', 0.85));
    return blob ? new File([blob], file.name.replace(/\.\w+$/, '') + '.jpg', { type: 'image/jpeg' }) : file;
  } catch {
    return file; // fall back to the original if the browser cannot decode it
  }
}

// The site-visit form: times, system size, photos of the finished roof, and the homeowner's signature.
export default function InstallationCompleteModal({ installation, onClose, onCompleted }) {
  const { addToast } = useToast();
  const [serials, setSerials] = useState([]);
  const [photos, setPhotos] = useState([]);
  const [uploading, setUploading] = useState(false);
  const [signedBy, setSignedBy] = useState('');
  const [signatureData, setSignatureData] = useState(null);
  const [signed, setSigned] = useState(null); // { name } once saved on the server
  const [savingSignature, setSavingSignature] = useState(false);
  const [start, setStart] = useState('');
  const [finish, setFinish] = useState('');
  const [size, setSize] = useState('');
  const [notes, setNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [padKey, setPadKey] = useState(0);

  const refreshPhotos = useCallback(async (id) => {
    setPhotos(await api.getInstallationPhotos(id));
  }, []);

  useEffect(() => {
    if (!installation) return;
    const now = new Date();
    setStart(installation.start_time ? toLocalInput(new Date(`${installation.start_time}Z`)) : toLocalInput(new Date(now.getTime() - 2 * 60 * 60 * 1000)));
    setFinish(toLocalInput(now));
    setSize(String(installation.system_capacity));
    setNotes('Installation and testing finished. Power generation verified.');
    setSignedBy(installation.signed_by_name || '');
    setSigned(installation.signed_by_name ? { name: installation.signed_by_name } : null);
    setSignatureData(null);
    setError(null);
    api.getInstallationSerials(installation.id).then(setSerials).catch(() => setSerials([]));
    refreshPhotos(installation.id).catch(() => setPhotos([]));
  }, [installation, refreshPhotos]);

  const handleFiles = async (event) => {
    const files = Array.from(event.target.files || []);
    event.target.value = '';
    if (files.length === 0) return;
    setUploading(true);
    try {
      for (const file of files) {
        const ready = await shrinkPhoto(file);
        await api.uploadInstallationPhoto(installation.id, ready);
      }
      await refreshPhotos(installation.id);
    } catch (err) {
      addToast(`Photo not saved: ${err.message}`, 'error', 6000);
    } finally {
      setUploading(false);
    }
  };

  const removePhoto = async (photo) => {
    try {
      await api.deleteInstallationPhoto(installation.id, photo.id);
      await refreshPhotos(installation.id);
    } catch (err) {
      addToast(`Could not remove the photo: ${err.message}`, 'error');
    }
  };

  const saveSignature = async () => {
    setSavingSignature(true);
    try {
      await api.saveInstallationSignature(installation.id, signedBy.trim(), signatureData);
      setSigned({ name: signedBy.trim() });
      addToast('Signature saved.', 'success');
    } catch (err) {
      addToast(`Signature not saved: ${err.message}`, 'error', 6000);
    } finally {
      setSavingSignature(false);
    }
  };

  const redoSignature = () => {
    setSigned(null);
    setSignatureData(null);
    setPadKey((k) => k + 1);
  };

  const ready = photos.length >= 1 && signed;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    try {
      setSubmitting(true);
      await api.completeInstallation(installation.id, {
        confirmed_system_size: parseFloat(size),
        serial_numbers: serials.map((s) => s.serial_number),
        // Send real moments in time, so the server does not have to guess our time zone
        start_time: new Date(start).toISOString(),
        finish_time: new Date(finish).toISOString(),
        notes,
      });
      addToast(`Job JOB-${String(installation.id).padStart(4, '0')} completed.`, 'success', 6000);
      onCompleted?.();
      onClose();
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  const field = 'w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:outline-none';
  const label = 'block text-xs font-semibold text-slate-700 mb-1';

  return (
    <Modal
      isOpen={Boolean(installation)}
      onClose={onClose}
      title={installation ? `Finish the job: JOB-${String(installation.id).padStart(4, '0')}` : 'Finish the job'}
      maxWidth="max-w-2xl"
    >
      {installation && (
        <form onSubmit={handleSubmit} className="space-y-5 text-sm">
          <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 text-xs flex justify-between">
            <span className="text-slate-500">Customer</span>
            <span className="font-bold text-slate-900">{installation.customer_name}</span>
          </div>

          <section className="space-y-3">
            <h4 className="text-sm font-bold text-slate-900">1. Times and size</h4>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div>
                <label className={label}>Work started</label>
                <input required type="datetime-local" value={start} onChange={(e) => setStart(e.target.value)} className={field} />
              </div>
              <div>
                <label className={label}>Work finished</label>
                <input required type="datetime-local" value={finish} onChange={(e) => setFinish(e.target.value)} className={field} />
              </div>
              <div>
                <label className={label}>Installed size (kW)</label>
                <input max="50" required type="number" step="0.1" min="0.5" value={size} onChange={(e) => setSize(e.target.value)} className={field} />
              </div>
            </div>
            <div>
              <label className={label}>Serial numbers installed</label>
              <div className="space-y-1 max-h-28 overflow-y-auto border border-slate-200 rounded-lg p-2 bg-slate-50">
                {serials.length === 0 ? (
                  <p className="text-xs text-slate-500 italic">Nothing has been dispatched for this job yet.</p>
                ) : (
                  serials.map((s) => (
                    <div key={s.id} className="flex justify-between items-center text-xs p-1.5 bg-white rounded border border-slate-200">
                      <span><span className="font-bold text-slate-800">{s.product_name}</span> <span className="text-slate-400">({s.category})</span></span>
                      <span className="font-mono font-semibold text-purple-700">{s.serial_number}</span>
                    </div>
                  ))
                )}
              </div>
            </div>
            <div>
              <label className={label}>Notes</label>
              <textarea maxLength={2000} rows={2} value={notes} onChange={(e) => setNotes(e.target.value)} className={field} />
            </div>
          </section>

          <section className="space-y-3">
            <h4 className="text-sm font-bold text-slate-900">2. Photos of the finished roof</h4>
            <label className="inline-flex items-center gap-2 px-3 py-2 border border-slate-300 rounded-lg text-xs font-semibold text-slate-700 hover:bg-slate-50 cursor-pointer">
              <Camera className="w-4 h-4" />
              {uploading ? 'Uploading...' : 'Take or choose photos'}
              <input type="file" accept="image/*" multiple capture="environment" onChange={handleFiles} disabled={uploading} className="hidden" />
            </label>
            {photos.length === 0 ? (
              <p className="text-xs text-rose-600">At least one photo is needed.</p>
            ) : (
              <div className="grid grid-cols-3 sm:grid-cols-4 gap-2">
                {photos.map((p) => (
                  <div key={p.id} className="relative group">
                    <img src={p.url} alt={p.caption || 'Finished roof'} className="w-full h-20 object-cover rounded-lg border border-slate-200" />
                    <button
                      type="button"
                      onClick={() => removePhoto(p)}
                      className="absolute -top-1.5 -right-1.5 bg-white border border-slate-300 rounded-full p-0.5 text-slate-600 hover:text-rose-600"
                      title="Remove this photo"
                    >
                      <X className="w-3 h-3" />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </section>

          <section className="space-y-3">
            <h4 className="text-sm font-bold text-slate-900">3. Homeowner accepts the work</h4>
            {signed ? (
              <div className="flex items-center justify-between bg-emerald-50 border border-emerald-200 rounded-lg p-3 text-xs">
                <span className="text-emerald-900">Signed by <strong>{signed.name}</strong>.</span>
                <button type="button" onClick={redoSignature} className="font-semibold text-emerald-800 hover:underline">Sign again</button>
              </div>
            ) : (
              <>
                <div>
                  <label className={label}>Homeowner's name</label>
                  <input maxLength={255} type="text" minLength={2} value={signedBy} onChange={(e) => setSignedBy(e.target.value)} placeholder="Full name" className={field} />
                </div>
                <SignaturePad key={padKey} onChange={setSignatureData} />
                <button
                  type="button"
                  onClick={saveSignature}
                  disabled={savingSignature || !signatureData || signedBy.trim().length < 2}
                  className="px-3 py-2 text-xs font-semibold rounded-lg bg-slate-900 hover:bg-slate-800 text-white transition disabled:opacity-40"
                >
                  {savingSignature ? 'Saving...' : 'Save signature'}
                </button>
              </>
            )}
          </section>

          {error && <div className="text-xs text-rose-700 bg-rose-50 border border-rose-200 rounded-lg p-2.5">{error}</div>}

          <div className="flex justify-end gap-3 pt-3 border-t border-slate-200">
            <button type="button" onClick={onClose} className="px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-100 transition">
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting || !ready}
              title={ready ? '' : 'Add at least one photo and the homeowner\'s signature first'}
              className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold rounded-lg transition disabled:opacity-50 flex items-center gap-1.5"
            >
              <CheckCircle2 className="w-4 h-4" />
              {submitting ? 'Saving...' : 'Mark job completed'}
            </button>
          </div>
        </form>
      )}
    </Modal>
  );
}
