import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import DataTable from '../components/DataTable';
import StatusBadge from '../components/StatusBadge';
import Modal from '../components/Modal';
import { LoadingState, ErrorState } from '../components/States';
import { useToast } from '../components/Toast';
import { Plus, UserPlus, Phone, Mail, MapPin, Zap } from 'lucide-react';

export default function Leads({ onCustomerCreated }) {
  const [leads, setLeads] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const { addToast } = useToast();

  const [formData, setFormData] = useState({
    name: '',
    phone: '',
    email: '',
    address: '',
    city: '',
    enquiry_source: 'Web',
    required_capacity: 5.0,
    monthly_electricity_bill: 5000,
    roof_area: 600,
    grid_type: 'On-Grid',
    subsidy_requirement: false,
    lead_status: 'New'
  });

  const fetchLeads = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.getLeads();
      setLeads(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchLeads();
  }, []);

  const handleCreate = async (e) => {
    e.preventDefault();
    try {
      setSubmitting(true);
      await api.createLead({
        ...formData,
        required_capacity: parseFloat(formData.required_capacity),
        monthly_electricity_bill: parseFloat(formData.monthly_electricity_bill),
        roof_area: parseFloat(formData.roof_area)
      });
      addToast('Lead created successfully!', 'success');
      setIsModalOpen(false);
      setFormData({
        name: '',
        phone: '',
        email: '',
        address: '',
        city: '',
        enquiry_source: 'Web',
        required_capacity: 5.0,
        monthly_electricity_bill: 5000,
        roof_area: 600,
        grid_type: 'On-Grid',
        subsidy_requirement: false,
        lead_status: 'New'
      });
      fetchLeads();
    } catch (err) {
      addToast(`Failed to create lead: ${err.message}`, 'error');
    } finally {
      setSubmitting(false);
    }
  };

  const handleConvert = async (leadId) => {
    try {
      const customer = await api.convertLead(leadId);
      addToast(`Lead successfully converted to Customer #${customer.id} (${customer.name})!`, 'success');
      fetchLeads();
      if (onCustomerCreated) onCustomerCreated(customer);
    } catch (err) {
      addToast(`Conversion failed: ${err.message}`, 'error');
    }
  };

  const columns = [
    {
      header: 'Lead Name & City',
      accessor: 'name',
      render: (row) => (
        <div>
          <div className="font-semibold text-slate-900">{row.name}</div>
          <div className="text-xs text-slate-500 flex items-center gap-1 mt-0.5">
            <MapPin className="w-3 h-3 text-slate-400" /> {row.city}
          </div>
        </div>
      )
    },
    {
      header: 'Contact Info',
      accessor: 'phone',
      render: (row) => (
        <div className="text-xs space-y-0.5">
          <div className="flex items-center gap-1 text-slate-700">
            <Phone className="w-3 h-3 text-slate-400" /> {row.phone}
          </div>
          <div className="flex items-center gap-1 text-slate-500">
            <Mail className="w-3 h-3 text-slate-400" /> {row.email}
          </div>
        </div>
      )
    },
    {
      header: 'Enquiry Source',
      accessor: 'enquiry_source',
      render: (row) => (
        <span className="px-2 py-0.5 rounded text-xs font-medium bg-slate-100 text-slate-700 border border-slate-200">
          {row.enquiry_source}
        </span>
      )
    },
    {
      header: 'Req. Capacity & Bill',
      accessor: 'required_capacity',
      render: (row) => (
        <div className="text-xs">
          <div className="font-semibold text-amber-700 flex items-center gap-1">
            <Zap className="w-3 h-3" /> {row.required_capacity} kW ({row.grid_type})
          </div>
          <div className="text-slate-500">Bill: ₹{row.monthly_electricity_bill?.toLocaleString()}/mo</div>
          <div className="text-slate-400 text-[11px]">Roof: {row.roof_area} sq.ft</div>
        </div>
      )
    },
    {
      header: 'Subsidy Req.',
      accessor: 'subsidy_requirement',
      render: (row) => (
        <span className={`px-2 py-0.5 rounded text-xs font-semibold ${row.subsidy_requirement ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' : 'bg-slate-100 text-slate-500'}`}>
          {row.subsidy_requirement ? 'Yes (Govt.)' : 'No'}
        </span>
      )
    },
    {
      header: 'Status',
      accessor: 'lead_status',
      render: (row) => <StatusBadge status={row.lead_status} />
    },
    {
      header: 'Action',
      accessor: 'id',
      render: (row) => (
        <div>
          {row.lead_status !== 'Converted' ? (
            <button
              onClick={() => handleConvert(row.id)}
              className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-md bg-emerald-600 text-white hover:bg-emerald-700 transition"
            >
              <UserPlus className="w-3.5 h-3.5" /> Convert to Customer
            </button>
          ) : (
            <span className="text-xs font-medium text-emerald-600">Converted (Cust #{row.customer_id})</span>
          )}
        </div>
      )
    }
  ];

  if (loading) return <LoadingState message="Loading rooftop solar leads..." />;
  if (error) return <ErrorState title="Failed to load leads" message={error} onRetry={fetchLeads} />;

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
        <div>
          <h3 className="text-lg font-bold text-slate-900">Solar Enquiries & Leads</h3>
          <p className="text-xs text-slate-500">Capture initial customer inquiries and qualify for site survey.</p>
        </div>
        <button
          onClick={() => setIsModalOpen(true)}
          className="inline-flex items-center gap-2 px-3.5 py-2 bg-amber-500 hover:bg-amber-600 text-slate-950 rounded-lg text-sm font-semibold shadow-xs transition"
        >
          <Plus className="w-4 h-4" /> Add New Lead
        </button>
      </div>

      <DataTable
        columns={columns}
        data={leads}
        searchPlaceholder="Search leads by name, phone, city..."
        emptyTitle="No leads captured"
        emptyDescription="Create your first enquiry to begin the Phase 1 sales pipeline."
      />

      {/* Create Lead Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title="Create New Solar Lead"
      >
        <form onSubmit={handleCreate} className="space-y-4 text-sm">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Customer Full Name *</label>
              <input
                required
                type="text"
                value={formData.name}
                onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                placeholder="e.g. Ramesh Chandra"
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Phone Number *</label>
              <input
                required
                type="text"
                value={formData.phone}
                onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                placeholder="+91 98765 43210"
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Email Address *</label>
              <input
                required
                type="email"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                placeholder="customer@example.com"
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">City *</label>
              <input
                required
                type="text"
                value={formData.city}
                onChange={(e) => setFormData({ ...formData, city: e.target.value })}
                placeholder="e.g. Hyderabad, Bengaluru"
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:outline-none"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Premises Address *</label>
            <textarea
              required
              rows={2}
              value={formData.address}
              onChange={(e) => setFormData({ ...formData, address: e.target.value })}
              placeholder="House/Plot No, Street, Landmark..."
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:outline-none"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Enquiry Source</label>
              <select
                value={formData.enquiry_source}
                onChange={(e) => setFormData({ ...formData, enquiry_source: e.target.value })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:outline-none bg-white"
              >
                <option value="Web">Web Form</option>
                <option value="WhatsApp">WhatsApp</option>
                <option value="Call">Phone Call</option>
                <option value="Manual">Manual Walk-in</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Required Capacity (kW)</label>
              <input
                type="number"
                step="0.5"
                min="1"
                max="50"
                value={formData.required_capacity}
                onChange={(e) => setFormData({ ...formData, required_capacity: e.target.value })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Grid Type</label>
              <select
                value={formData.grid_type}
                onChange={(e) => setFormData({ ...formData, grid_type: e.target.value })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:outline-none bg-white"
              >
                <option value="On-Grid">On-Grid (Connected)</option>
                <option value="Off-Grid">Off-Grid (Battery Backup)</option>
                <option value="Hybrid">Hybrid</option>
              </select>
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Monthly Electricity Bill (₹)</label>
              <input
                type="number"
                step="100"
                value={formData.monthly_electricity_bill}
                onChange={(e) => setFormData({ ...formData, monthly_electricity_bill: e.target.value })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Roof Area (sq.ft)</label>
              <input
                type="number"
                step="10"
                value={formData.roof_area}
                onChange={(e) => setFormData({ ...formData, roof_area: e.target.value })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:outline-none"
              />
            </div>
          </div>

          <div className="pt-2">
            <label className="flex items-center gap-2 cursor-pointer">
              <input
                type="checkbox"
                checked={formData.subsidy_requirement}
                onChange={(e) => setFormData({ ...formData, subsidy_requirement: e.target.checked })}
                className="w-4 h-4 text-amber-600 rounded border-slate-300 focus:ring-amber-500"
              />
              <span className="text-xs font-semibold text-slate-800">Govt. Rooftop Subsidy Required (Yes/No)</span>
            </label>
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
              {submitting ? 'Creating...' : 'Save Lead'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
