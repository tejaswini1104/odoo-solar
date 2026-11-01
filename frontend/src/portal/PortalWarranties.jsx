import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import DataTable from '../components/DataTable';
import StatusBadge from '../components/StatusBadge';
import { LoadingState, ErrorState } from '../components/States';

const formatDate = (value) => new Date(value).toLocaleDateString('en-IN');

export default function PortalWarranties() {
  const [warranties, setWarranties] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = async () => {
    try {
      setLoading(true);
      setError(null);
      setWarranties(await api.getMyWarranties());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  if (loading) return <LoadingState message="Loading your warranties..." />;
  if (error) return <ErrorState title="Could not load warranties" message={error} onRetry={load} />;

  const columns = [
    {
      header: 'Equipment',
      accessor: 'product_name',
      render: (row) => (
        <div className="text-xs">
          <div className="font-semibold text-slate-900">{row.product_name}</div>
          <div className="text-slate-500">{row.category}</div>
        </div>
      )
    },
    {
      header: 'Serial number',
      accessor: 'serial_number',
      render: (row) =>
        row.serial_number ? (
          <span className="font-mono text-xs font-bold text-purple-700">{row.serial_number}</span>
        ) : (
          <span className="text-xs italic text-slate-500">All solar panels (one warranty for the whole system)</span>
        )
    },
    {
      header: 'Coverage',
      accessor: 'duration_months',
      render: (row) => (
        <div className="text-xs">
          <div>{row.duration_months / 12} years</div>
          <div className="text-slate-500">{formatDate(row.start_date)} to {formatDate(row.end_date)}</div>
        </div>
      )
    },
    {
      header: 'Status',
      accessor: 'status',
      render: (row) => (
        <div className="text-xs space-y-1">
          <StatusBadge status={row.status} />
          {row.status === 'Active' && <div className="text-slate-500">{row.days_left.toLocaleString('en-IN')} days left</div>}
        </div>
      )
    },
  ];

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-bold text-slate-900">My warranties</h2>
        <p className="text-xs text-slate-500">
          Coverage starts on the day your installation was completed. Repairs on equipment under an active warranty are free.
        </p>
      </div>
      <DataTable
        columns={columns}
        data={warranties}
        searchPlaceholder="Search by equipment or serial number..."
        emptyTitle="No warranties yet"
        emptyDescription="Warranties appear here after your installation is completed."
      />
    </div>
  );
}
