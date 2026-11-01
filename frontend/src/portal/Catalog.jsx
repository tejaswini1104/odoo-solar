import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api/client';
import { LoadingState, ErrorState, EmptyState } from '../components/States';

export default function Catalog() {
  const [packages, setPackages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  const load = async () => {
    try {
      setLoading(true);
      setError(null);
      setPackages(await api.getPortalPackages());
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  if (loading) return <LoadingState message="Loading packages..." />;
  if (error) return <ErrorState title="Could not load packages" message={error} onRetry={load} />;
  if (packages.length === 0) {
    return <EmptyState title="No packages available" description="Please check back later." />;
  }

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-lg font-bold text-slate-900">Solar packages</h2>
        <p className="text-xs text-slate-500">Prices include GST. A surveyor visits your roof before a final quotation is issued.</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {packages.map((pkg) => (
          <div key={pkg.id} className="bg-white rounded-xl border border-slate-200 p-5 flex flex-col justify-between">
            <div>
              <div className="flex items-center justify-between">
                <h3 className="font-bold text-slate-900">{pkg.capacity_kw} kW {pkg.system_type}</h3>
                <span className="text-xs font-semibold px-2 py-0.5 rounded-full bg-slate-100 text-slate-700">
                  {pkg.system_type}
                </span>
              </div>
              <p className="text-xs text-slate-500 mt-2">{pkg.description}</p>
            </div>
            <div className="flex items-center justify-between mt-5">
              <div>
                <div className="text-xs text-slate-500">Indicative price</div>
                <div className="text-xl font-extrabold text-slate-900">₹{pkg.price_incl_gst.toLocaleString('en-IN')}</div>
              </div>
              <button
                onClick={() =>
                  navigate(`/portal/enquire?kw=${pkg.capacity_kw}&type=${encodeURIComponent(pkg.system_type)}`)
                }
                className="px-3 py-2 text-xs font-semibold rounded-lg bg-amber-500 hover:bg-amber-600 text-slate-950 transition"
              >
                Enquire about this
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
