import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import Modal from '../components/Modal';
import { LoadingState, ErrorState } from '../components/States';
import { Package, Zap, Cpu, Layers, Eye } from 'lucide-react';

export default function SolarPackages() {
  const [packages, setPackages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedBOM, setSelectedBOM] = useState(null);
  const [bomLoading, setBomLoading] = useState(false);

  const fetchPackages = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.getPackages();
      setPackages(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchPackages();
  }, []);

  const handleViewBOM = async (pkgId) => {
    try {
      setBomLoading(true);
      const bom = await api.getPackageBOM(pkgId);
      setSelectedBOM(bom);
    } catch (err) {
      alert(`Failed to load BOM: ${err.message}`);
    } finally {
      setBomLoading(false);
    }
  };

  if (loading) return <LoadingState message="Loading standardized solar packages..." />;
  if (error) return <ErrorState title="Failed to load packages" message={error} onRetry={fetchPackages} />;

  return (
    <div className="space-y-6">
      <div>
        <h3 className="text-lg font-bold text-slate-900">Standardized Solar Packages</h3>
        <p className="text-xs text-slate-500">
          Turnkey 1kW - 5kW On-Grid and Off-Grid packages with automated Bill of Materials (BOM).
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {packages.map((pkg) => (
          <div
            key={pkg.id}
            className="bg-white rounded-xl border border-slate-200 p-5 shadow-xs hover:border-amber-300 hover:shadow-md transition flex flex-col justify-between"
          >
            <div>
              <div className="flex items-center justify-between mb-3">
                <span className={`px-2 py-0.5 rounded text-xs font-bold uppercase ${pkg.system_type === 'On-Grid' ? 'bg-sky-50 text-sky-700 border border-sky-200' : 'bg-purple-50 text-purple-700 border border-purple-200'}`}>
                  {pkg.system_type}
                </span>
                <span className="text-xs font-bold text-amber-600 bg-amber-50 px-2 py-0.5 rounded border border-amber-200">
                  {pkg.capacity_kw} kW
                </span>
              </div>

              <h4 className="text-base font-bold text-slate-900 mb-1">{pkg.name}</h4>
              <p className="text-xs text-slate-500 line-clamp-2 mb-4">{pkg.description}</p>

              <div className="border-t border-slate-100 pt-3 text-xs text-slate-600 space-y-1">
                <div className="flex justify-between">
                  <span>Components in BOM:</span>
                  <span className="font-semibold text-slate-800">{pkg.components?.length || 0} items</span>
                </div>
                <div className="flex justify-between">
                  <span>Standard Base Price:</span>
                  <span className="font-semibold text-slate-800">₹{pkg.base_price?.toLocaleString()}</span>
                </div>
              </div>
            </div>

            <button
              onClick={() => handleViewBOM(pkg.id)}
              className="mt-4 w-full flex items-center justify-center gap-2 py-2 text-xs font-semibold rounded-lg bg-slate-100 hover:bg-amber-500 hover:text-slate-950 text-slate-700 transition"
            >
              <Eye className="w-3.5 h-3.5" /> View Auto BOM
            </button>
          </div>
        ))}
      </div>

      {/* Auto BOM Details Modal */}
      <Modal
        isOpen={!!selectedBOM}
        onClose={() => setSelectedBOM(null)}
        title={selectedBOM ? `Automatic BOM: ${selectedBOM.package_name}` : 'BOM Details'}
        maxWidth="max-w-3xl"
      >
        {selectedBOM && (
          <div className="space-y-4">
            <div className="flex items-center justify-between bg-slate-50 p-3 rounded-lg border border-slate-200 text-xs">
              <div>
                <span className="text-slate-500">System Capacity: </span>
                <strong className="text-slate-900">{selectedBOM.capacity_kw} kW</strong>
                <span className="mx-2 text-slate-300">|</span>
                <span className="text-slate-500">Architecture: </span>
                <strong className="text-slate-900">{selectedBOM.system_type}</strong>
              </div>
              <span className="px-2 py-0.5 rounded bg-emerald-50 text-emerald-700 font-semibold border border-emerald-200">
                Auto-Mapped Components
              </span>
            </div>

            <div className="border border-slate-200 rounded-lg overflow-hidden">
              <table className="w-full text-left text-xs text-slate-700">
                <thead className="bg-slate-100 text-slate-600 uppercase font-semibold">
                  <tr>
                    <th className="px-4 py-2.5">Component / Product</th>
                    <th className="px-3 py-2.5">Category</th>
                    <th className="px-3 py-2.5">Qty</th>
                    <th className="px-3 py-2.5">Unit Price</th>
                    <th className="px-4 py-2.5 text-right">Line Total</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-200">
                  {selectedBOM.items.map((item, idx) => (
                    <tr key={idx} className="hover:bg-slate-50">
                      <td className="px-4 py-2.5">
                        <div className="font-medium text-slate-900">{item.product_name}</div>
                        {item.is_serialized && (
                          <span className="text-[10px] text-purple-600 font-semibold">
                            [Serialized Tracking Required]
                          </span>
                        )}
                      </td>
                      <td className="px-3 py-2.5 text-slate-500">{item.category}</td>
                      <td className="px-3 py-2.5 font-bold text-slate-800">
                        {item.quantity} {item.unit}
                      </td>
                      <td className="px-3 py-2.5">₹{item.unit_price?.toLocaleString()}</td>
                      <td className="px-4 py-2.5 text-right font-semibold text-slate-900">
                        ₹{item.total_price?.toLocaleString()}
                      </td>
                    </tr>
                  ))}
                </tbody>
                <tfoot className="bg-slate-50 border-t border-slate-200 font-semibold">
                  <tr>
                    <td colSpan={4} className="px-4 py-2 text-right text-slate-600">Subtotal:</td>
                    <td className="px-4 py-2 text-right">₹{selectedBOM.subtotal?.toLocaleString()}</td>
                  </tr>
                  <tr>
                    <td colSpan={4} className="px-4 py-1.5 text-right text-slate-600">GST (18%):</td>
                    <td className="px-4 py-1.5 text-right">₹{selectedBOM.tax?.toLocaleString()}</td>
                  </tr>
                  <tr className="text-sm font-bold text-amber-700 border-t border-slate-300">
                    <td colSpan={4} className="px-4 py-2.5 text-right">Total Turnkey Quote:</td>
                    <td className="px-4 py-2.5 text-right">₹{selectedBOM.total?.toLocaleString()}</td>
                  </tr>
                </tfoot>
              </table>
            </div>

            <div className="flex justify-end pt-2">
              <button
                onClick={() => setSelectedBOM(null)}
                className="px-4 py-2 bg-slate-800 text-white rounded-lg text-xs font-semibold hover:bg-slate-900 transition"
              >
                Close BOM View
              </button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
}
