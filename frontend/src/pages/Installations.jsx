import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import DataTable from '../components/DataTable';
import StatusBadge from '../components/StatusBadge';
import Modal from '../components/Modal';
import { LoadingState, ErrorState } from '../components/States';
import { useToast } from '../components/Toast';
import { Wrench, CheckCircle2, ShieldCheck, Calendar, User, Zap } from 'lucide-react';

export default function Installations({ setActiveTab }) {
  const [installations, setInstallations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [completeModalInst, setCompleteModalInst] = useState(null);
  const [instSerials, setInstSerials] = useState([]);
  const [confirmedSize, setConfirmedSize] = useState(5.0);
  const [completionNotes, setCompletionNotes] = useState('');
  const [submittingComplete, setSubmittingComplete] = useState(false);
  const { addToast } = useToast();

  const fetchInstallations = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.getInstallations();
      setInstallations(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchInstallations();
  }, []);

  const handleOpenComplete = async (inst) => {
    try {
      setCompleteModalInst(inst);
      setConfirmedSize(inst.system_capacity);
      setCompletionNotes(`Completed rooftop installation and testing. Generation verified.`);
      const serials = await api.getInstallationSerials(inst.id);
      setInstSerials(serials);
    } catch (err) {
      addToast(`Error: ${err.message}`, 'error');
    }
  };

  const handleMarkComplete = async (e) => {
    e.preventDefault();
    if (!completeModalInst) return;

    try {
      setSubmittingComplete(true);
      const serialNumbers = instSerials.map((s) => s.serial_number);
      await api.completeInstallation(completeModalInst.id, {
        confirmed_system_size: parseFloat(confirmedSize),
        serial_numbers: serialNumbers,
        notes: completionNotes
      });

      addToast(
        `Installation #${completeModalInst.id} Completed! System size ${confirmedSize}kW confirmed. Warranties automatically created!`,
        'success',
        6000
      );
      setCompleteModalInst(null);
      fetchInstallations();
      if (setActiveTab) setActiveTab('warranties');
    } catch (err) {
      addToast(`Completion Failed: ${err.message}`, 'error');
    } finally {
      setSubmittingComplete(false);
    }
  };

  const columns = [
    {
      header: 'Job ID & Customer',
      accessor: 'id',
      render: (row) => (
        <div>
          <span className="font-mono text-xs font-bold text-slate-800">JOB-{row.id.toString().padStart(4, '0')}</span>
          <div className="font-semibold text-slate-900 mt-0.5">{row.customer_name}</div>
          <div className="text-[11px] text-slate-400">SO-{row.sales_order_id.toString().padStart(4, '0')}</div>
        </div>
      )
    },
    {
      header: 'Assigned Crew',
      accessor: 'technician_name',
      render: (row) => (
        <div className="text-xs flex items-center gap-1.5 text-slate-700">
          <User className="w-3.5 h-3.5 text-slate-400" />
          <span className="font-medium">{row.technician_name}</span>
        </div>
      )
    },
    {
      header: 'Scheduled Date',
      accessor: 'scheduled_date',
      render: (row) => (
        <div className="text-xs flex items-center gap-1.5 text-slate-600">
          <Calendar className="w-3.5 h-3.5 text-slate-400" />
          <span>{new Date(row.scheduled_date).toLocaleDateString()}</span>
        </div>
      )
    },
    {
      header: 'System Capacity',
      accessor: 'system_capacity',
      render: (row) => (
        <div className="text-xs">
          <div className="font-bold text-amber-700 flex items-center gap-1">
            <Zap className="w-3 h-3" /> {row.system_capacity} kW
          </div>
          {row.confirmed_system_size && (
            <span className="text-[10px] text-emerald-600 font-semibold">
              Confirmed: {row.confirmed_system_size} kW
            </span>
          )}
        </div>
      )
    },
    {
      header: 'Installation Status',
      accessor: 'status',
      render: (row) => <StatusBadge status={row.status} />
    },
    {
      header: 'Action',
      accessor: 'id',
      render: (row) => (
        <div>
          {row.status !== 'Completed' ? (
            <button
              onClick={() => handleOpenComplete(row)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white transition shadow-xs"
            >
              <CheckCircle2 className="w-3.5 h-3.5" /> Mark Completed
            </button>
          ) : (
            <div className="text-xs">
              <span className="font-medium text-emerald-600">✓ Warranties Active</span>
              <div className="text-[10px] text-slate-400">
                {row.finish_time ? new Date(row.finish_time).toLocaleDateString() : 'Done'}
              </div>
            </div>
          )}
        </div>
      )
    }
  ];

  if (loading) return <LoadingState message="Loading rooftop installation jobs..." />;
  if (error) return <ErrorState title="Failed to load installations" message={error} onRetry={fetchInstallations} />;

  return (
    <div className="space-y-4">
      {/* Policy banner */}
      <div className="bg-teal-50 border border-teal-200 rounded-xl p-3.5 text-xs text-teal-950 flex items-start gap-3">
        <ShieldCheck className="w-5 h-5 text-teal-600 shrink-0 mt-0.5" />
        <div>
          <strong>AUTOMATIC WARRANTY ENGINE TRIGGER:</strong> When an installation is marked completed, the backend
          automatically computes and generates Warranty records for every serialized product (Inverter: 2yr, Battery:
          2yr, Charge Controller: 2yr) plus 20-year bulk Solar Panel warranty. Start date = completion date; End date is
          computed automatically.
        </div>
      </div>

      <div className="flex justify-between items-center">
        <div>
          <h3 className="text-lg font-bold text-slate-900">Rooftop Installation Jobs</h3>
          <p className="text-xs text-slate-500">Track technician schedules and confirm system size to activate warranties.</p>
        </div>
      </div>

      <DataTable
        columns={columns}
        data={installations}
        searchPlaceholder="Search installations by customer or technician..."
      />

      {/* Mark Completed Modal */}
      <Modal
        isOpen={!!completeModalInst}
        onClose={() => setCompleteModalInst(null)}
        title={completeModalInst ? `Confirm Completion: JOB-${completeModalInst.id.toString().padStart(4, '0')}` : 'Complete'}
      >
        {completeModalInst && (
          <form onSubmit={handleMarkComplete} className="space-y-4 text-sm">
            <div className="p-3 bg-slate-50 rounded-lg border border-slate-200 text-xs">
              <div className="flex justify-between">
                <span className="text-slate-500">Customer:</span>
                <span className="font-bold text-slate-900">{completeModalInst.customer_name}</span>
              </div>
              <div className="flex justify-between mt-1">
                <span className="text-slate-500">Assigned Crew:</span>
                <span className="font-semibold text-slate-800">{completeModalInst.technician_name}</span>
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Confirmed System Capacity (kW) *
              </label>
              <input
                required
                type="number"
                step="0.1"
                min="0.5"
                value={confirmedSize}
                onChange={(e) => setConfirmedSize(e.target.value)}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:outline-none"
              />
              <p className="text-[11px] text-slate-500 mt-1">
                Verify actual nameplate kW capacity installed on the customer's roof.
              </p>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">
                Linked Serial Numbers for Installed Hardware:
              </label>
              <div className="space-y-1.5 max-h-36 overflow-y-auto border border-slate-200 rounded-lg p-2.5 bg-slate-50">
                {instSerials.length === 0 ? (
                  <p className="text-xs text-slate-500 italic">No serials dispatched yet for this order.</p>
                ) : (
                  instSerials.map((s) => (
                    <div key={s.id} className="flex justify-between items-center text-xs p-1.5 bg-white rounded border border-slate-200">
                      <div>
                        <span className="font-bold text-slate-800">{s.product_name}</span>
                        <span className="text-slate-400 text-[11px] ml-1.5">({s.category})</span>
                      </div>
                      <span className="font-mono font-semibold text-purple-700 bg-purple-50 px-2 py-0.5 rounded border border-purple-200">
                        {s.serial_number}
                      </span>
                    </div>
                  ))
                )}
              </div>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Installation Notes / Checklist</label>
              <textarea
                rows={2}
                value={completionNotes}
                onChange={(e) => setCompletionNotes(e.target.value)}
                placeholder="Earthing testing ohms, AC voltage, inverter display sync..."
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:outline-none"
              />
            </div>

            <div className="flex justify-end gap-3 pt-4 border-t border-slate-200">
              <button
                type="button"
                onClick={() => setCompleteModalInst(null)}
                className="px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-100 transition"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={submittingComplete}
                className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white font-semibold rounded-lg transition disabled:opacity-50 flex items-center gap-1.5"
              >
                <CheckCircle2 className="w-4 h-4" />
                {submittingComplete ? 'Saving & Creating Warranties...' : 'Mark Completed & Activate Warranties'}
              </button>
            </div>
          </form>
        )}
      </Modal>
    </div>
  );
}
