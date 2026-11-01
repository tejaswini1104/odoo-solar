import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import DataTable from '../components/DataTable';
import StatusBadge from '../components/StatusBadge';
import Modal from '../components/Modal';
import { LoadingState, ErrorState } from '../components/States';
import { useToast } from '../components/Toast';
import { Plus, Check, X, ShieldAlert, Compass, User, Wrench } from 'lucide-react';
import { useAuth } from '../auth/AuthContext';
import SurveyFindingsModal from '../components/SurveyFindingsModal';

export default function SiteSurveys() {
  const { user } = useAuth();
  // Sales and technicians work on surveys. Technicians measure, and only Sales approve or reject.
  const canWrite = user?.role === 'sales' || user?.role === 'technician';
  const [surveys, setSurveys] = useState([]);
  const [customers, setCustomers] = useState([]);
  const [technicians, setTechnicians] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [findingsFor, setFindingsFor] = useState(null);
  const isTechnician = user?.role === 'technician';
  const isSales = user?.role === 'sales';
  const awaitingDecision = (row) => row.status === 'Submitted' || row.status === 'Draft';
  const { addToast } = useToast();

  const [formData, setFormData] = useState({
    customer_id: '',
    technician_name: 'Suresh Varma',
    roof_area: 700,
    roof_direction: 'South',
    roof_tilt: 20,
    shading_level: 'Low',
    cable_distance: 18,
    grid_suitability: 'Suitable',
    recommended_capacity: 5.0,
    survey_notes: '',
    status: 'Draft'
  });

  const loadData = async () => {
    try {
      setLoading(true);
      setError(null);
      const [survData, custData, techData] = await Promise.all([
        api.getSurveys(),
        api.getCustomers(),
        api.getTechnicians()
      ]);
      setSurveys(survData);
      setCustomers(custData);
      setTechnicians(techData);
      if (custData.length > 0 && !formData.customer_id) {
        setFormData((prev) => ({ ...prev, customer_id: custData[0].id }));
      }
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleApprove = async (id) => {
    try {
      await api.approveSurvey(id);
      addToast(`Survey #${id} has been APPROVED! Quotations can now be generated.`, 'success');
      loadData();
    } catch (err) {
      addToast(`Approval failed: ${err.message}`, 'error');
    }
  };

  const handleReject = async (id) => {
    try {
      await api.rejectSurvey(id);
      addToast(`Survey #${id} has been REJECTED.`, 'info');
      loadData();
    } catch (err) {
      addToast(`Reject failed: ${err.message}`, 'error');
    }
  };

  const handleReassign = async (survey, technicianId) => {
    try {
      await api.reassignSurvey(survey.id, technicianId);
      addToast('Survey reassigned. It now appears on the new technician\'s list.', 'success');
      loadData();
    } catch (err) {
      addToast(`Could not reassign: ${err.message}`, 'error', 6000);
    }
  };

  const handleCreate = async (e) => {
    e.preventDefault();
    try {
      setSubmitting(true);
      await api.createSurvey({
        ...formData,
        customer_id: parseInt(formData.customer_id),
        roof_area: parseFloat(formData.roof_area),
        roof_tilt: parseFloat(formData.roof_tilt),
        cable_distance: parseFloat(formData.cable_distance),
        recommended_capacity: parseFloat(formData.recommended_capacity),
      });
      addToast('Site Survey created successfully!', 'success');
      setIsModalOpen(false);
      loadData();
    } catch (err) {
      addToast(`Failed to create survey: ${err.message}`, 'error');
    } finally {
      setSubmitting(false);
    }
  };

  const columns = [
    {
      header: 'Survey ID & Customer',
      accessor: 'id',
      render: (row) => {
        const cust = customers.find((c) => c.id === row.customer_id);
        return (
          <div>
            <span className="font-mono text-xs font-bold text-slate-800">SURV-{row.id.toString().padStart(4, '0')}</span>
            <div className="font-semibold text-slate-900 mt-0.5">
              {cust ? cust.name : `Customer #${row.customer_id || 'N/A'}`}
            </div>
          </div>
        );
      }
    },
    {
      header: 'Roof Technical Specs',
      accessor: 'roof_area',
      render: (row) =>
        row.roof_area == null ? (
          <div className="text-xs text-slate-600 space-y-0.5">
            <div className="font-semibold text-slate-800">
              Visit on {row.scheduled_date ? new Date(row.scheduled_date).toLocaleDateString('en-IN') : 'a date to be set'}
            </div>
            <div>Measurements not recorded yet</div>
            {row.survey_notes && <div className="text-slate-500 truncate max-w-[14rem]">{row.survey_notes}</div>}
          </div>
        ) : (
          <div className="text-xs space-y-0.5">
            <div><strong className="text-slate-800">Area:</strong> {row.roof_area} sq.ft</div>
            <div><strong className="text-slate-800">Orientation:</strong> {row.roof_direction} ({row.roof_tilt}°)</div>
            <div><strong className="text-slate-800">Shading:</strong> <span className={row.shading_level === 'High' ? 'text-rose-600 font-bold' : 'text-slate-600'}>{row.shading_level}</span></div>
          </div>
        )
    },
    {
      header: 'Grid & Cable Distance',
      accessor: 'grid_suitability',
      render: (row) =>
        row.roof_area == null ? (
          <span className="text-xs text-slate-400">-</span>
        ) : (
          <div className="text-xs space-y-0.5">
            <div><strong className="text-slate-800">Grid:</strong> {row.grid_suitability}</div>
            <div><strong className="text-slate-800">Cable Run:</strong> {row.cable_distance}m</div>
            <div className="text-amber-700 font-bold mt-1">
              Rec. {row.recommended_capacity} kW{row.recommended_system_type ? ` ${row.recommended_system_type}` : ''}
            </div>
          </div>
        )
    },
    {
      header: 'Technician',
      accessor: 'technician_name',
      render: (row) =>
        isSales && row.status === 'Scheduled' ? (
          <select
            value={row.technician_id || ''}
            onChange={(e) => handleReassign(row, Number(e.target.value))}
            className="px-2 py-1 border border-slate-300 rounded text-xs bg-white focus:ring-1 focus:ring-amber-500"
            title="Sales can hand the visit to another technician"
          >
            {technicians.map((t) => (
              <option key={t.id} value={t.id}>{t.name}</option>
            ))}
          </select>
        ) : (
          <div className="text-xs flex items-center gap-1.5 text-slate-700">
            <Wrench className="w-3.5 h-3.5 text-slate-400" />
            <span>{row.technician_name}</span>
          </div>
        )
    },
    {
      header: 'Hard Gate Status',
      accessor: 'status',
      render: (row) => (
        <div>
          <StatusBadge status={row.status} />
          {row.status === 'Approved' ? (
            <p className="text-[10px] text-emerald-600 mt-0.5 font-medium">✓ Ready for Quotation</p>
          ) : row.status === 'Scheduled' ? (
            <p className="text-[10px] text-slate-500 mt-0.5 font-medium">Waiting for the site visit</p>
          ) : (
            <p className="text-[10px] text-rose-500 mt-0.5 font-medium">⚠ Quotation Blocked</p>
          )}
        </div>
      )
    },
    {
      header: 'Approval Actions',
      accessor: 'id',
      render: (row) => (
        <div className="flex items-center gap-1.5">
          {row.status === 'Scheduled' && isTechnician && (
            <button
              onClick={() => setFindingsFor(row)}
              className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-semibold rounded bg-amber-500 text-slate-950 hover:bg-amber-600 transition"
            >
              Record findings
            </button>
          )}
          {row.status === 'Scheduled' && !isTechnician && (
            <span className="text-xs text-slate-500 font-medium">Awaiting the visit</span>
          )}
          {isSales && awaitingDecision(row) && (
            <button
              onClick={() => handleApprove(row.id)}
              className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-semibold rounded bg-emerald-600 text-white hover:bg-emerald-700 transition"
              title="Approve Survey to unlock Quotation creation"
            >
              <Check className="w-3.5 h-3.5" /> Approve
            </button>
          )}
          {isSales && awaitingDecision(row) && (
            <button
              onClick={() => handleReject(row.id)}
              className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-semibold rounded border border-rose-300 text-rose-700 hover:bg-rose-50 transition"
              title="Reject Survey"
            >
              <X className="w-3.5 h-3.5" /> Reject
            </button>
          )}
        </div>
      )
    }
  ];

  if (loading) return <LoadingState message="Loading site surveys..." />;
  if (error) return <ErrorState title="Failed to load surveys" message={error} onRetry={loadData} />;

  return (
    <div className="space-y-4">
      {/* Hard Gate Reminder Banner */}
      <div className="bg-amber-50 border border-amber-200 rounded-xl p-4 flex items-start gap-3 shadow-xs">
        <ShieldAlert className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
        <div className="text-xs text-amber-900">
          <span className="font-bold">CRITICAL HARD GATE ENFORCED:</span> A quotation cannot be created unless the
          linked site survey's status is <strong>"Approved"</strong>. This is enforced directly in the backend service
          layer. If an unapproved survey is used to generate a quote, the API rejects the request with HTTP 400.
        </div>
      </div>

      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
        <div>
          <h3 className="text-lg font-bold text-slate-900">Technical Site Surveys</h3>
          <p className="text-xs text-slate-500">Rooftop inspection parameters, shading assessment, and hard approval gate.</p>
        </div>
        {canWrite && (
          <button
            onClick={() => setIsModalOpen(true)}
            className="inline-flex items-center gap-2 px-3.5 py-2 bg-amber-500 hover:bg-amber-600 text-slate-950 rounded-lg text-sm font-semibold shadow-xs transition"
          >
            <Plus className="w-4 h-4" /> New Site Survey
          </button>
        )}
      </div>

      <SurveyFindingsModal
        survey={findingsFor}
        customerName={customers.find((c) => findingsFor && c.id === findingsFor.customer_id)?.name}
        onClose={() => setFindingsFor(null)}
        onSaved={loadData}
      />

      <DataTable
        columns={columns}
        data={surveys}
        searchPlaceholder="Search surveys by customer or technician..."
      />

      {/* Create Survey Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title="Conduct Rooftop Site Survey"
      >
        <form onSubmit={handleCreate} className="space-y-4 text-sm">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Select Customer *</label>
              <select
                required
                value={formData.customer_id}
                onChange={(e) => setFormData({ ...formData, customer_id: e.target.value })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:outline-none bg-white"
              >
                {customers.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name} ({c.city})
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Assigned Technician *</label>
              <select
                value={formData.technician_name}
                onChange={(e) => setFormData({ ...formData, technician_name: e.target.value })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:outline-none bg-white"
              >
                {technicians.map((t) => (
                  <option key={t.id} value={t.name}>
                    {t.name}
                  </option>
                ))}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Roof Area (sq.ft) *</label>
              <input min="1" max="100000"
                required
                type="number"
                step="10"
                value={formData.roof_area}
                onChange={(e) => setFormData({ ...formData, roof_area: e.target.value })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Roof Direction *</label>
              <select
                value={formData.roof_direction}
                onChange={(e) => setFormData({ ...formData, roof_direction: e.target.value })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:outline-none bg-white"
              >
                <option value="South">South (Optimal)</option>
                <option value="South-West">South-West</option>
                <option value="South-East">South-East</option>
                <option value="East">East</option>
                <option value="West">West</option>
                <option value="North">North (Not recommended)</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Roof Tilt (Degrees)</label>
              <input min="0" max="90"
                type="number"
                step="1"
                value={formData.roof_tilt}
                onChange={(e) => setFormData({ ...formData, roof_tilt: e.target.value })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:outline-none"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Shading Level</label>
              <select
                value={formData.shading_level}
                onChange={(e) => setFormData({ ...formData, shading_level: e.target.value })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:outline-none bg-white"
              >
                <option value="None">None (Full Sun)</option>
                <option value="Low">Low (&lt;10%)</option>
                <option value="Medium">Medium (10-30%)</option>
                <option value="High">High (&gt;30%)</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Cable Run to Inverter (m)</label>
              <input min="0" max="1000"
                type="number"
                step="1"
                value={formData.cable_distance}
                onChange={(e) => setFormData({ ...formData, cable_distance: e.target.value })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Recommended kW</label>
              <input min="1" max="5"
                type="number"
                step="0.5"
                value={formData.recommended_capacity}
                onChange={(e) => setFormData({ ...formData, recommended_capacity: e.target.value })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:outline-none"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Grid Suitability</label>
              <select
                value={formData.grid_suitability}
                onChange={(e) => setFormData({ ...formData, grid_suitability: e.target.value })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:outline-none bg-white"
              >
                <option value="Suitable">Suitable (Stable voltage & phase)</option>
                <option value="Needs Upgrade">Needs DISCOM Transformer Upgrade</option>
                <option value="Unsuitable">Unsuitable</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Initial Status</label>
              <select
                value={formData.status}
                onChange={(e) => setFormData({ ...formData, status: e.target.value })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:outline-none bg-white"
              >
                <option value="Draft">Draft (Unapproved - blocks quote)</option>
                <option value="Submitted">Submitted for Review</option>
              </select>
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Survey Notes & Remarks</label>
            <textarea maxLength={2000}
              rows={2}
              value={formData.survey_notes}
              onChange={(e) => setFormData({ ...formData, survey_notes: e.target.value })}
              placeholder="Structure notes, DISCOM meter location, accessibility..."
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:outline-none"
            />
          </div>

          <div className="flex justify-end gap-3 pt-4 border-t border-slate-200">
            <button
              type="button"
              onClick={() => setIsModalOpen(false)}
              className="px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-100 transition"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="px-4 py-2 bg-amber-500 hover:bg-amber-600 text-slate-950 font-semibold rounded-lg transition disabled:opacity-50"
            >
              {submitting ? 'Submitting...' : 'Save Survey'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
