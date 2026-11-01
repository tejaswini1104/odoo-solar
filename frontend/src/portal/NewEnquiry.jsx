import React, { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { api } from '../api/client';
import { useToast } from '../components/Toast';

const CAPACITIES = [1, 2, 3, 4, 5];

export default function NewEnquiry() {
  const [params] = useSearchParams();
  const navigate = useNavigate();
  const { addToast } = useToast();
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  // Pre-filled when the customer clicks "Enquire about this" on a package
  const initialCapacity = Number(params.get('kw')) || 3;
  const initialType = params.get('type') === 'Off-Grid' ? 'Off-Grid' : 'On-Grid';

  const [form, setForm] = useState({
    required_capacity: CAPACITIES.includes(initialCapacity) ? initialCapacity : 3,
    grid_type: initialType,
    monthly_electricity_bill: '',
    roof_area: '',
    subsidy_requirement: false,
  });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      const created = await api.createEnquiry({
        required_capacity: Number(form.required_capacity),
        grid_type: form.grid_type,
        monthly_electricity_bill: Number(form.monthly_electricity_bill),
        roof_area: Number(form.roof_area),
        subsidy_requirement: form.subsidy_requirement,
      });
      addToast(`Enquiry ${created.reference} received. Our sales team will contact you.`, 'success', 6000);
      navigate('/portal/enquiries');
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="max-w-xl bg-white rounded-xl border border-slate-200 p-6">
      <h2 className="text-lg font-bold text-slate-900">New solar enquiry</h2>
      <p className="text-xs text-slate-500 mb-5">Tell us about your home or business and we will get back to you.</p>

      <form onSubmit={handleSubmit} className="space-y-4 text-sm">
        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-1">System size</label>
          <select
            value={form.required_capacity}
            onChange={(e) => setForm({ ...form, required_capacity: e.target.value })}
            className="w-full px-3 py-2 border border-slate-300 rounded-lg bg-white focus:ring-2 focus:ring-amber-500 focus:outline-none"
          >
            {CAPACITIES.map((kw) => (
              <option key={kw} value={kw}>{kw} kW</option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-1">Connection type</label>
          <select
            value={form.grid_type}
            onChange={(e) => setForm({ ...form, grid_type: e.target.value })}
            className="w-full px-3 py-2 border border-slate-300 rounded-lg bg-white focus:ring-2 focus:ring-amber-500 focus:outline-none"
          >
            <option value="On-Grid">On-Grid (connected to the electricity grid)</option>
            <option value="Off-Grid">Off-Grid (with battery backup)</option>
          </select>
        </div>

        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-1">Monthly electricity bill (₹)</label>
          <input max="10000000"
            required
            type="number"
            min="0"
            step="0.01"
            value={form.monthly_electricity_bill}
            onChange={(e) => setForm({ ...form, monthly_electricity_bill: e.target.value })}
            className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:outline-none"
          />
        </div>

        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-1">Shadow-free roof area (sq.ft)</label>
          <input max="100000"
            required
            type="number"
            min="1"
            step="0.01"
            value={form.roof_area}
            onChange={(e) => setForm({ ...form, roof_area: e.target.value })}
            className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:outline-none"
          />
        </div>

        <label className="flex items-center gap-2 text-xs text-slate-700">
          <input
            type="checkbox"
            checked={form.subsidy_requirement}
            onChange={(e) => setForm({ ...form, subsidy_requirement: e.target.checked })}
          />
          I would like help with the government rooftop subsidy
        </label>

        {error && (
          <div className="text-xs text-rose-700 bg-rose-50 border border-rose-200 rounded-lg p-2.5">{error}</div>
        )}

        <button
          type="submit"
          disabled={submitting}
          className="px-4 py-2 bg-amber-500 hover:bg-amber-600 text-slate-950 font-semibold rounded-lg transition disabled:opacity-50"
        >
          {submitting ? 'Sending...' : 'Send enquiry'}
        </button>
      </form>
    </div>
  );
}
