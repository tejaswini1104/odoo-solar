import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import DataTable from '../components/DataTable';
import StatusBadge from '../components/StatusBadge';
import Modal from '../components/Modal';
import { LoadingState, ErrorState } from '../components/States';
import { useToast } from '../components/Toast';
import { Plus, UserPlus, Phone, Mail, MapPin, Zap } from 'lucide-react';
import { useAuth } from '../auth/AuthContext';

export default function Leads({ onCustomerCreated }) {
  const { user } = useAuth();
  const isSales = user?.role === 'sales'; // only Sales add and convert leads
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

  const handleStatus = async (leadId, status) => {
    try {
      await api.setLeadStatus(leadId, status);
      addToast(`Lead marked ${status === 'New' ? 'open again' : status.toLowerCase()}.`, 'success');
      fetchLeads();
    } catch (err) {
      addToast(`Could not update the lead: ${err.message}`, 'error');
    }
  };

  // The first call: roof space without shadow, the grid connection and what the customer said
  const [callLead, setCallLead] = useState(null);
  const [call, setCall] = useState({ shadow_free_area: '', grid_connection_ok: 'yes', call_notes: '' });

  const openCall = (lead) => {
    setCall({
      shadow_free_area: lead.shadow_free_area ?? lead.roof_area ?? '',
      grid_connection_ok: lead.grid_connection_ok === false ? 'no' : 'yes',
      call_notes: lead.call_notes || '',
    });
    setCallLead(lead);
  };

  const saveCall = async (e) => {
    e.preventDefault();
    try {
      setSubmitting(true);
      await api.setLeadStatus(callLead.id, 'Contacted', {
        shadow_free_area: parseFloat(call.shadow_free_area),
        grid_connection_ok: call.grid_connection_ok === 'yes',
        call_notes: call.call_notes,
      });
      addToast(
        call.grid_connection_ok === 'yes'
          ? 'Call recorded. You can now book the site survey.'
          : 'Call recorded. The grid connection is unsuitable, so a survey cannot be booked until that changes.',
        'success',
        6000,
      );
      setCallLead(null);
      fetchLeads();
    } catch (err) {
      addToast(`Could not save the call: ${err.message}`, 'error');
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
      render: (row) => (
        <div className="space-y-1">
          <StatusBadge status={row.lead_status} />
          {row.contacted_at && (
            <div className="text-[11px] text-slate-500">
              Shadow-free roof {row.shadow_free_area} sq.ft ·{' '}
              <span className={row.grid_connection_ok ? 'text-emerald-700' : 'text-rose-700 font-semibold'}>
                grid {row.grid_connection_ok ? 'suitable' : 'unsuitable'}
              </span>
            </div>
          )}
          {row.lead_status === 'New' && <div className="text-[11px] text-amber-700">Needs a call before a survey</div>}
        </div>
      )
    },
    {
      header: 'Action',
      accessor: 'id',
      render: (row) => (
        <div>
          {row.lead_status !== 'Converted' && !isSales ? (
            <span className="text-xs text-slate-500 font-medium">Sales converts leads</span>
          ) : row.lead_status !== 'Converted' ? (
            <div className="flex flex-col items-start gap-1.5">
              <button
                onClick={() => handleConvert(row.id)}
                className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs font-medium rounded-md bg-emerald-600 text-white hover:bg-emerald-700 transition"
              >
                <UserPlus className="w-3.5 h-3.5" /> Convert to Customer
              </button>
              <div className="flex gap-1.5">
                {['New', 'Contacted'].includes(row.lead_status) && (
                  <button
                    onClick={() => openCall(row)}
                    className="px-2 py-0.5 text-[11px] font-semibold rounded border border-slate-300 text-slate-700 hover:bg-slate-100 transition"
                  >
                    {row.lead_status === 'New' ? 'Record first call' : 'Update call'}
                  </button>
                )}
                {row.lead_status !== 'Lost' && (
                  <button
                    onClick={() => handleStatus(row.id, 'Lost')}
                    className="px-2 py-0.5 text-[11px] font-semibold rounded border border-rose-300 text-rose-700 hover:bg-rose-50 transition"
                  >
                    Mark lost
                  </button>
                )}
                {row.lead_status === 'Lost' && (
                  <button
                    onClick={() => handleStatus(row.id, 'New')}
                    className="px-2 py-0.5 text-[11px] font-semibold rounded border border-slate-300 text-slate-700 hover:bg-slate-100 transition"
                  >
                    Reopen
                  </button>
                )}
              </div>
            </div>
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
        {isSales && (
          <button
            onClick={() => setIsModalOpen(true)}
            className="inline-flex items-center gap-2 px-3.5 py-2 bg-amber-500 hover:bg-amber-600 text-slate-950 rounded-lg text-sm font-semibold shadow-xs transition"
          >
            <Plus className="w-4 h-4" /> Add New Lead
          </button>
        )}
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
              <input maxLength={255}
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
              <input maxLength={14}
                required
                type="text"
                value={formData.phone}
                onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                pattern="(\+91|91|0)?[ -]?[6-9][0-9]{9}"
                title="Enter a 10 digit mobile number, for example 9876543210"
                placeholder="98765 43210"
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Email Address *</label>
              <input maxLength={255}
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
              <input maxLength={100}
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
            <textarea maxLength={500}
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
              <input min="0" max="10000000"
                type="number"
                step="100"
                value={formData.monthly_electricity_bill}
                onChange={(e) => setFormData({ ...formData, monthly_electricity_bill: e.target.value })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Roof Area (sq.ft)</label>
              <input min="1" max="100000"
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
      <Modal isOpen={!!callLead} onClose={() => setCallLead(null)} title={`First call: ${callLead?.name || ''}`} maxWidth="max-w-md">
        <form onSubmit={saveCall} className="space-y-4 text-sm">
          <p className="text-xs text-slate-600">
            Check the basics by phone before sending a technician. They said their bill is
            ₹{callLead?.monthly_electricity_bill?.toLocaleString()}/month and the roof is about {callLead?.roof_area} sq.ft.
          </p>
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Shadow-free roof space (sq.ft)</label>
            <input max="100000" required type="number" min="1" step="any" value={call.shadow_free_area}
              onChange={(e) => setCall({ ...call, shadow_free_area: e.target.value })}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:outline-none" />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Is the grid connection suitable?</label>
            <select value={call.grid_connection_ok} onChange={(e) => setCall({ ...call, grid_connection_ok: e.target.value })}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:outline-none">
              <option value="yes">Yes, suitable</option>
              <option value="no">No, not suitable</option>
            </select>
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Notes from the call</label>
            <textarea rows={3} maxLength={1000} value={call.call_notes} onChange={(e) => setCall({ ...call, call_notes: e.target.value })}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:outline-none" />
          </div>
          <div className="flex justify-end gap-3 pt-3 border-t border-slate-200">
            <button type="button" onClick={() => setCallLead(null)} className="px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-100 text-xs">Cancel</button>
            <button type="submit" disabled={submitting} className="px-4 py-2 bg-amber-500 hover:bg-amber-600 text-slate-950 font-semibold rounded-lg text-xs disabled:opacity-50">
              {submitting ? 'Saving...' : 'Save call'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
