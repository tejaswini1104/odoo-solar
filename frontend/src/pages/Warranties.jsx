import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import DataTable from '../components/DataTable';
import StatusBadge from '../components/StatusBadge';
import { LoadingState, ErrorState } from '../components/States';
import { ShieldCheck, ShieldAlert, Search, Calendar, Cpu } from 'lucide-react';

export default function Warranties() {
  const [warranties, setWarranties] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchSerial, setSearchSerial] = useState('');

  const fetchWarranties = async (serial = '') => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.getWarranties(serial);
      setWarranties(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchWarranties();
  }, []);

  const handleSearch = (e) => {
    e.preventDefault();
    fetchWarranties(searchSerial);
  };

  const columns = [
    {
      header: 'Customer & Serial Number',
      accessor: 'serial_number',
      render: (row) => (
        <div>
          <div className="font-semibold text-slate-900">{row.customer_name}</div>
          {row.serial_number ? (
            <span className="font-mono text-xs font-bold text-purple-700 bg-purple-50 px-2 py-0.5 rounded border border-purple-200 mt-0.5 inline-block">
              {row.serial_number}
            </span>
          ) : (
            <span className="text-xs text-slate-500 font-medium italic">
              [Bulk Order Warranty - All Panels]
            </span>
          )}
        </div>
      )
    },
    {
      header: 'Product & Category',
      accessor: 'product_name',
      render: (row) => (
        <div className="text-xs">
          <div className="font-medium text-slate-800">{row.product_name}</div>
          <div className="text-slate-500">{row.category}</div>
        </div>
      )
    },
    {
      header: 'Warranty Duration',
      accessor: 'duration_months',
      render: (row) => (
        <span className="text-xs font-semibold px-2 py-0.5 rounded bg-slate-100 text-slate-700">
          {row.duration_months} Months ({row.duration_months / 12} Years)
        </span>
      )
    },
    {
      header: 'Coverage Validity Window',
      accessor: 'start_date',
      render: (row) => (
        <div className="text-xs space-y-0.5">
          <div className="text-slate-600">
            <strong>Start:</strong> {new Date(row.start_date).toLocaleDateString()}
          </div>
          <div className="text-slate-600">
            <strong>End:</strong> {new Date(row.end_date).toLocaleDateString()}
          </div>
        </div>
      )
    },
    {
      header: 'Live Status',
      accessor: 'status',
      render: (row) => <StatusBadge status={row.status} />
    }
  ];

  if (loading) return <LoadingState message="Loading warranty records..." />;
  if (error) return <ErrorState title="Failed to load warranties" message={error} onRetry={() => fetchWarranties()} />;

  return (
    <div className="space-y-4">
      {/* Policy banner */}
      <div className="bg-sky-50 border border-sky-200 rounded-xl p-3.5 text-xs text-sky-950 flex items-start gap-3">
        <ShieldCheck className="w-5 h-5 text-sky-600 shrink-0 mt-0.5" />
        <div>
          <strong>CENTRAL WARRANTY REGISTRY:</strong> Inverters (2yr), Batteries (2yr), and Charge Controllers (2yr) are
          tracked by unique serial number. Solar Panels are covered under a 20-year bulk order warranty.
          All start dates match completion date, and expiration is automatically evaluated when customer service calls come in.
        </div>
      </div>

      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
        <div>
          <h3 className="text-lg font-bold text-slate-900">Equipment Warranties</h3>
          <p className="text-xs text-slate-500">Automated coverage registry calculated from job completion dates.</p>
        </div>

        {/* Quick serial search */}
        <form onSubmit={handleSearch} className="flex gap-2 w-full sm:w-auto">
          <input
            type="text"
            value={searchSerial}
            onChange={(e) => setSearchSerial(e.target.value)}
            placeholder="Search Serial (e.g. INV-2026-0042)"
            className="px-3 py-1.5 border border-slate-300 rounded-lg text-xs font-mono w-full sm:w-60 focus:ring-2 focus:ring-amber-500"
          />
          <button
            type="submit"
            className="px-3 py-1.5 bg-slate-800 text-white rounded-lg text-xs font-semibold hover:bg-slate-900 transition flex items-center gap-1"
          >
            <Search className="w-3.5 h-3.5" /> Lookup
          </button>
        </form>
      </div>

      <DataTable
        columns={columns}
        data={warranties}
        searchPlaceholder="Filter warranties..."
      />
    </div>
  );
}
