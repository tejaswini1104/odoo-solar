import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import DataTable from '../components/DataTable';
import StatusBadge from '../components/StatusBadge';
import { LoadingState, ErrorState } from '../components/States';

export default function MyEnquiries() {
  const [enquiries, setEnquiries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = async () => {
    try {
      setLoading(true);
      setError(null);
      setEnquiries(await api.getMyEnquiries());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  if (loading) return <LoadingState message="Loading your enquiries..." />;
  if (error) return <ErrorState title="Could not load enquiries" message={error} onRetry={load} />;

  const columns = [
    {
      header: 'Reference',
      accessor: 'reference',
      render: (row) => <span className="font-mono text-xs font-bold text-slate-800">{row.reference}</span>
    },
    {
      header: 'System',
      accessor: 'required_capacity',
      render: (row) => <span className="text-xs">{row.required_capacity} kW {row.grid_type}</span>
    },
    {
      header: 'Monthly bill',
      accessor: 'monthly_electricity_bill',
      render: (row) => <span className="text-xs">₹{row.monthly_electricity_bill.toLocaleString('en-IN')}</span>
    },
    {
      header: 'Roof area',
      accessor: 'roof_area',
      render: (row) => <span className="text-xs">{row.roof_area} sq.ft</span>
    },
    {
      header: 'Status',
      accessor: 'lead_status',
      render: (row) => <StatusBadge status={row.lead_status === 'New' ? 'Open' : row.lead_status} />
    },
    {
      header: 'Received',
      accessor: 'created_at',
      render: (row) => <span className="text-xs">{new Date(row.created_at).toLocaleDateString('en-IN')}</span>
    },
  ];

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-bold text-slate-900">My enquiries</h2>
        <p className="text-xs text-slate-500">Track the enquiries you have sent to SunPower.</p>
      </div>
      <DataTable
        columns={columns}
        data={enquiries}
        searchPlaceholder="Search your enquiries..."
        emptyTitle="No enquiries yet"
        emptyDescription="Choose a package and send an enquiry to get started."
      />
    </div>
  );
}
