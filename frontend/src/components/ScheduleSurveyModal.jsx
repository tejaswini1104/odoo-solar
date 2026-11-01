import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import Modal from './Modal';
import { useToast } from './Toast';
import { localIsoDate } from '../utils/dates';

const todayIso = () => localIsoDate();

// Sales book a site visit for a customer. The system chooses the technician with the least open work.
export default function ScheduleSurveyModal({ customer, onClose, onScheduled }) {
  const { addToast } = useToast();
  const [date, setDate] = useState(todayIso());
  const [notes, setNotes] = useState('');
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (customer) {
      setDate(todayIso());
      setNotes('');
    }
  }, [customer]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    try {
      setSubmitting(true);
      const survey = await api.scheduleSurvey({
        customer_id: customer.id,
        scheduled_date: date,
        notes: notes.trim() || null,
      });
      addToast(
        `Survey booked for ${new Date(survey.scheduled_date).toLocaleDateString('en-IN')}. ${survey.technician_name} has been assigned and will see it on their list.`,
        'success',
        7000
      );
      onScheduled?.(survey);
      onClose();
    } catch (err) {
      addToast(`Could not schedule: ${err.message}`, 'error', 6000);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal
      isOpen={Boolean(customer)}
      onClose={onClose}
      title={customer ? `Schedule a site survey for ${customer.name}` : 'Schedule a site survey'}
      maxWidth="max-w-md"
    >
      <form onSubmit={handleSubmit} className="space-y-4 text-sm">
        {customer && (
          <div className="text-xs text-slate-600 bg-slate-50 border border-slate-200 rounded-lg p-3">
            {customer.address}, {customer.city}
            <br />
            {customer.phone}
          </div>
        )}
        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-1">Visit date</label>
          <input
            required
            type="date"
            min={todayIso()}
            value={date}
            onChange={(e) => setDate(e.target.value)}
            className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:outline-none"
          />
        </div>
        <div>
          <label className="block text-xs font-semibold text-slate-700 mb-1">Notes for the technician (optional)</label>
          <textarea
            rows={3}
            maxLength={1000}
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
            placeholder="Gate code, best time to call, anything about the roof"
            className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:outline-none"
          />
        </div>
        <p className="text-[11px] text-slate-500">
          The technician with the least open work is assigned automatically, and the visit appears on their list.
        </p>
        <div className="flex justify-end gap-3 pt-3 border-t border-slate-200">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-100 transition text-xs"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={submitting}
            className="px-4 py-2 bg-amber-500 hover:bg-amber-600 text-slate-950 font-semibold rounded-lg transition text-xs disabled:opacity-50"
          >
            {submitting ? 'Scheduling...' : 'Schedule survey'}
          </button>
        </div>
      </form>
    </Modal>
  );
}
