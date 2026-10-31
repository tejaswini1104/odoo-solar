import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import DataTable from '../components/DataTable';
import Modal from '../components/Modal';
import { LoadingState, ErrorState } from '../components/States';
import { useToast } from '../components/Toast';
import { Plus, Phone, Mail, MapPin, User } from 'lucide-react';

export default function Customers() {
  const [customers, setCustomers] = useState([]);
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
    city: ''
  });

  const fetchCustomers = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await api.getCustomers();
      setCustomers(data);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCustomers();
  }, []);

  const handleCreate = async (e) => {
    e.preventDefault();
    try {
      setSubmitting(true);
      await api.createCustomer(formData);
      addToast('Customer record created successfully!', 'success');
      setIsModalOpen(false);
      setFormData({ name: '', phone: '', email: '', address: '', city: '' });
      fetchCustomers();
    } catch (err) {
      addToast(`Error creating customer: ${err.message}`, 'error');
    } finally {
      setSubmitting(false);
    }
  };

  const columns = [
    {
      header: 'Customer ID',
      accessor: 'id',
      render: (row) => <span className="font-mono text-xs font-bold text-slate-700">CUST-{row.id.toString().padStart(4, '0')}</span>
    },
    {
      header: 'Full Name',
      accessor: 'name',
      render: (row) => (
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-full bg-amber-100 text-amber-800 flex items-center justify-center font-bold text-xs">
            {row.name.charAt(0)}
          </div>
          <span className="font-semibold text-slate-900">{row.name}</span>
        </div>
      )
    },
    {
      header: 'Phone Number',
      accessor: 'phone',
      render: (row) => (
        <div className="flex items-center gap-1.5 text-xs text-slate-700">
          <Phone className="w-3.5 h-3.5 text-slate-400" /> {row.phone}
        </div>
      )
    },
    {
      header: 'Email Address',
      accessor: 'email',
      render: (row) => (
        <div className="flex items-center gap-1.5 text-xs text-slate-600">
          <Mail className="w-3.5 h-3.5 text-slate-400" /> {row.email}
        </div>
      )
    },
    {
      header: 'City & Address',
      accessor: 'city',
      render: (row) => (
        <div className="text-xs">
          <div className="font-medium text-slate-800">{row.city}</div>
          <div className="text-slate-500 truncate max-w-xs">{row.address}</div>
        </div>
      )
    },
    {
      header: 'Registered Date',
      accessor: 'created_at',
      render: (row) => (
        <span className="text-xs text-slate-500">
          {new Date(row.created_at).toLocaleDateString()}
        </span>
      )
    }
  ];

  if (loading) return <LoadingState message="Loading customers..." />;
  if (error) return <ErrorState title="Failed to load customers" message={error} onRetry={fetchCustomers} />;

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
        <div>
          <h3 className="text-lg font-bold text-slate-900">Registered Customers</h3>
          <p className="text-xs text-slate-500">Accounts converted from leads or registered directly for solar projects.</p>
        </div>
        <button
          onClick={() => setIsModalOpen(true)}
          className="inline-flex items-center gap-2 px-3.5 py-2 bg-amber-500 hover:bg-amber-600 text-slate-950 rounded-lg text-sm font-semibold shadow-xs transition"
        >
          <Plus className="w-4 h-4" /> Add Customer
        </button>
      </div>

      <DataTable
        columns={columns}
        data={customers}
        searchPlaceholder="Search customers by name, phone, city..."
      />

      {/* Create Customer Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title="Add New Customer"
      >
        <form onSubmit={handleCreate} className="space-y-4 text-sm">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Full Name *</label>
            <input
              required
              type="text"
              value={formData.name}
              onChange={(e) => setFormData({ ...formData, name: e.target.value })}
              placeholder="e.g. Ravi Kumar"
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:outline-none"
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Phone *</label>
              <input
                required
                type="text"
                value={formData.phone}
                onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                placeholder="+91 98480 12345"
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:outline-none"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Email *</label>
              <input
                required
                type="email"
                value={formData.email}
                onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                placeholder="ravi.kumar@example.com"
                className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:outline-none"
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">City *</label>
            <input
              required
              type="text"
              value={formData.city}
              onChange={(e) => setFormData({ ...formData, city: e.target.value })}
              placeholder="e.g. Hyderabad"
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Address *</label>
            <textarea
              required
              rows={2}
              value={formData.address}
              onChange={(e) => setFormData({ ...formData, address: e.target.value })}
              placeholder="Plot/Flat, Street name, Locality"
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
              {submitting ? 'Saving...' : 'Create Customer'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
