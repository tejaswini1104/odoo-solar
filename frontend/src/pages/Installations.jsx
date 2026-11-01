import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import DataTable from '../components/DataTable';
import StatusBadge from '../components/StatusBadge';
import InstallationCompleteModal from '../components/InstallationCompleteModal';
import InstallationProofModal from '../components/InstallationProofModal';
import { LoadingState, ErrorState } from '../components/States';
import { useToast } from '../components/Toast';
import { CheckCircle2, ShieldCheck, Calendar, User, Zap } from 'lucide-react';
import { useAuth } from '../auth/AuthContext';

export default function Installations({ setActiveTab }) {
  const { user } = useAuth();
  const isTechnician = user?.role === 'technician'; // technicians complete their own jobs
  const isSales = user?.role === 'sales';           // Sales decide which technician goes to which site
  const [technicians, setTechnicians] = useState([]);
  const [installations, setInstallations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [completeFor, setCompleteFor] = useState(null);
  const [proofFor, setProofFor] = useState(null);
  const { addToast } = useToast();

  const fetchInstallations = async () => {
    try {
      setLoading(true);
      setError(null);
      const [data, crew] = await Promise.all([
        api.getInstallations(),
        isSales ? api.getTechnicians() : Promise.resolve([]),
      ]);
      setInstallations(data);
      setTechnicians(crew);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleAssign = async (installation, technicianId) => {
    try {
      await api.assignTechnician(installation.id, technicianId);
      addToast('Technician assigned. The job now appears on their list.', 'success');
      fetchInstallations();
    } catch (err) {
      addToast(`Could not assign: ${err.message}`, 'error', 6000);
    }
  };

  useEffect(() => {
    fetchInstallations();
  }, []);

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
      render: (row) =>
        isSales && row.status !== 'Completed' ? (
          <select
            value={row.technician_id || ''}
            onChange={(e) => handleAssign(row, Number(e.target.value))}
            className="px-2 py-1 border border-slate-300 rounded text-xs bg-white focus:ring-1 focus:ring-amber-500"
          >
            {technicians.map((t) => (
              <option key={t.id} value={t.id}>{t.name}</option>
            ))}
          </select>
        ) : (
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
          {row.status !== 'Completed' && !isTechnician ? (
            <span className="text-xs text-slate-500 font-medium">Technician completes</span>
          ) : row.status !== 'Completed' ? (
            <button
              onClick={() => setCompleteFor(row)}
              className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg bg-emerald-600 hover:bg-emerald-700 text-white transition shadow-xs"
            >
              <CheckCircle2 className="w-3.5 h-3.5" /> Finish the job
            </button>
          ) : (
            <div className="text-xs space-y-0.5">
              <span className="font-medium text-emerald-600">✓ Completed</span>
              <div className="text-[10px] text-slate-400">
                {row.finish_time ? new Date(`${row.finish_time}Z`).toLocaleDateString('en-IN') : 'Done'}
                {' · '}{row.photo_count} photo{row.photo_count === 1 ? '' : 's'}
              </div>
              <button
                onClick={() => setProofFor(row)}
                className="text-[11px] font-semibold text-blue-600 hover:underline"
              >
                View proof
              </button>
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
          <strong>PROOF OF WORK:</strong> A job is complete only when the technician has recorded the start and finish
          times, taken photos of the finished roof, and the homeowner has signed on the screen to accept the work.
          Warranties start when the goods are delivered, or at completion if delivery was not recorded.
        </div>
      </div>

      <div className="flex justify-between items-center">
        <div>
          <h3 className="text-lg font-bold text-slate-900">Rooftop Installation Jobs</h3>
          <p className="text-xs text-slate-500">Track technician schedules and keep the proof of every finished job.</p>
        </div>
      </div>

      <DataTable
        columns={columns}
        data={installations}
        searchPlaceholder="Search installations by customer or technician..."
      />

      <InstallationCompleteModal
        installation={completeFor}
        onClose={() => setCompleteFor(null)}
        onCompleted={fetchInstallations}
      />
      <InstallationProofModal installation={proofFor} onClose={() => setProofFor(null)} />
    </div>
  );
}
