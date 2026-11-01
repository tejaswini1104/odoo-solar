import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import Modal from './Modal';
import { useToast } from './Toast';

const DIRECTIONS = ['North', 'North-East', 'East', 'South-East', 'South', 'South-West', 'West', 'North-West'];
const EMPTY = {
  roof_area: '',
  roof_direction: 'South',
  roof_tilt: '',
  shading_level: 'Low',
  cable_distance: '',
  grid_suitability: 'Suitable',
  recommended_capacity: '3',
  recommended_system_type: 'On-Grid',
  survey_notes: '',
};

// The technician records what they measured on the roof. The survey then waits for approval.
export default function SurveyFindingsModal({ survey, customerName, onClose, onSaved }) {
  const { addToast } = useToast();
  const [form, setForm] = useState(EMPTY);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (survey) {
      setForm(EMPTY);
      setError(null);
    }
  }, [survey]);

  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    try {
      setSubmitting(true);
      await api.completeSurvey(survey.id, {
        roof_area: Number(form.roof_area),
        roof_direction: form.roof_direction,
        roof_tilt: Number(form.roof_tilt),
        shading_level: form.shading_level,
        cable_distance: Number(form.cable_distance),
        grid_suitability: form.grid_suitability,
        recommended_capacity: Number(form.recommended_capacity),
        recommended_system_type: form.recommended_system_type,
        survey_notes: form.survey_notes.trim() || null,
      });
      addToast('Findings recorded. The survey now waits for approval.', 'success');
      onSaved?.();
      onClose();
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  const field = 'w-full px-3 py-2 border border-slate-300 rounded-lg bg-white focus:ring-2 focus:ring-amber-500 focus:outline-none';
  const label = 'block text-xs font-semibold text-slate-700 mb-1';

  return (
    <Modal
      isOpen={Boolean(survey)}
      onClose={onClose}
      title={survey ? `Record findings: SURV-${String(survey.id).padStart(4, '0')}${customerName ? ` (${customerName})` : ''}` : 'Record findings'}
      maxWidth="max-w-xl"
    >
      <form onSubmit={handleSubmit} className="space-y-4 text-sm">
        {survey?.survey_notes && (
          <div className="text-xs text-amber-900 bg-amber-50 border border-amber-200 rounded-lg p-3">
            <strong>Note from the office:</strong> {survey.survey_notes}
          </div>
        )}

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div>
            <label className={label}>Shadow-free roof area (sq.ft)</label>
            <input max="100000" required type="number" min="1" step="0.1" value={form.roof_area} onChange={set('roof_area')} className={field} />
          </div>
          <div>
            <label className={label}>Roof direction</label>
            <select value={form.roof_direction} onChange={set('roof_direction')} className={field}>
              {DIRECTIONS.map((d) => <option key={d}>{d}</option>)}
            </select>
          </div>
          <div>
            <label className={label}>Roof tilt (degrees)</label>
            <input required type="number" min="0" max="90" step="0.1" value={form.roof_tilt} onChange={set('roof_tilt')} className={field} />
          </div>
          <div>
            <label className={label}>Shading</label>
            <select value={form.shading_level} onChange={set('shading_level')} className={field}>
              {['None', 'Low', 'Medium', 'High'].map((s) => <option key={s}>{s}</option>)}
            </select>
          </div>
          <div>
            <label className={label}>Cable distance (metres)</label>
            <input max="1000" required type="number" min="0" step="0.1" value={form.cable_distance} onChange={set('cable_distance')} className={field} />
          </div>
          <div>
            <label className={label}>Grid connection</label>
            <select value={form.grid_suitability} onChange={set('grid_suitability')} className={field}>
              {['Suitable', 'Needs Upgrade', 'Unsuitable'].map((s) => <option key={s}>{s}</option>)}
            </select>
          </div>
          <div>
            <label className={label}>Recommended size (kW)</label>
            <select value={form.recommended_capacity} onChange={set('recommended_capacity')} className={field}>
              {[1, 2, 3, 4, 5].map((kw) => <option key={kw} value={kw}>{kw} kW</option>)}
            </select>
          </div>
          <div>
            <label className={label}>Recommended type</label>
            <select value={form.recommended_system_type} onChange={set('recommended_system_type')} className={field}>
              <option value="On-Grid">On-Grid</option>
              <option value="Off-Grid">Off-Grid (with battery)</option>
            </select>
          </div>
        </div>

        <div>
          <label className={label}>Notes</label>
          <textarea rows={3} maxLength={2000} value={form.survey_notes} onChange={set('survey_notes')} className={field} />
        </div>

        <p className="text-[11px] text-slate-500">
          The recommended size and type decide which package is quoted, so choose them carefully.
        </p>

        {error && <div className="text-xs text-rose-700 bg-rose-50 border border-rose-200 rounded-lg p-2.5">{error}</div>}

        <div className="flex justify-end gap-3 pt-3 border-t border-slate-200">
          <button type="button" onClick={onClose} className="px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-100 transition text-xs">
            Cancel
          </button>
          <button type="submit" disabled={submitting} className="px-4 py-2 bg-amber-500 hover:bg-amber-600 text-slate-950 font-semibold rounded-lg transition text-xs disabled:opacity-50">
            {submitting ? 'Saving...' : 'Submit findings'}
          </button>
        </div>
      </form>
    </Modal>
  );
}
