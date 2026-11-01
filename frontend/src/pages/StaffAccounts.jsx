import React, { useEffect, useState } from 'react';
import { Plus } from 'lucide-react';
import { api } from '../api/client';
import { useAuth } from '../auth/AuthContext';
import { ROLE_LABELS } from '../auth/access';
import DataTable from '../components/DataTable';
import Modal from '../components/Modal';
import { LoadingState, ErrorState } from '../components/States';
import { useToast } from '../components/Toast';

const STAFF_ROLE_OPTIONS = ['sales', 'technician', 'support', 'warehouse', 'admin'];
const EMPTY_FORM = { name: '', email: '', phone: '', password: '', role: 'sales', technician_id: '' };

export default function StaffAccounts() {
  const { user: me } = useAuth();
  const { addToast } = useToast();
  const [staff, setStaff] = useState([]);
  const [technicians, setTechnicians] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState(EMPTY_FORM);
  const [submitting, setSubmitting] = useState(false);

  const load = async () => {
    try {
      setLoading(true);
      setError(null);
      const [staffData, technicianData] = await Promise.all([api.getStaffAccounts(), api.getTechnicians()]);
      setStaff(staffData);
      setTechnicians(technicianData);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
  }, []);

  // Technician records that do not have a login yet
  const linked = new Set(staff.map((s) => s.technician_id).filter(Boolean));
  const freeTechnicians = technicians.filter((t) => !linked.has(t.id));

  const handleCreate = async (e) => {
    e.preventDefault();
    try {
      setSubmitting(true);
      const body = {
        name: form.name,
        email: form.email,
        phone: form.phone || null,
        password: form.password,
        role: form.role,
      };
      if (form.role === 'technician' && form.technician_id) body.technician_id = Number(form.technician_id);
      const created = await api.createStaffAccount(body);
      addToast(`${ROLE_LABELS[created.role]} account created for ${created.email}.`, 'success');
      setModalOpen(false);
      setForm(EMPTY_FORM);
      load();
    } catch (err) {
      addToast(`Could not create the account: ${err.message}`, 'error', 6000);
    } finally {
      setSubmitting(false);
    }
  };

  const toggleActive = async (account) => {
    try {
      if (account.is_active) await api.deactivateStaff(account.id);
      else await api.activateStaff(account.id);
      addToast(`${account.name} is now ${account.is_active ? 'switched off' : 'switched on'}.`, 'success');
      load();
    } catch (err) {
      addToast(err.message, 'error', 6000);
    }
  };

  if (loading) return <LoadingState message="Loading staff accounts..." />;
  if (error) return <ErrorState title="Could not load staff accounts" message={error} onRetry={load} />;

  const columns = [
    {
      header: 'Name',
      accessor: 'name',
      render: (row) => (
        <div className="text-xs">
          <div className="font-semibold text-slate-900">{row.name}</div>
          <div className="text-slate-500">{row.email}</div>
        </div>
      )
    },
    {
      header: 'Role',
      accessor: 'role',
      render: (row) => <span className="text-xs font-semibold text-slate-700">{ROLE_LABELS[row.role] || row.role}</span>
    },
    {
      header: 'Technician record',
      accessor: 'technician_id',
      render: (row) => {
        const record = technicians.find((t) => t.id === row.technician_id);
        return <span className="text-xs text-slate-600">{record ? record.name : '-'}</span>;
      }
    },
    {
      header: 'Status',
      accessor: 'is_active',
      render: (row) => (
        <span className={`text-xs font-semibold px-2 py-0.5 rounded-full ${row.is_active ? 'bg-emerald-50 text-emerald-700' : 'bg-slate-100 text-slate-500'}`}>
          {row.is_active ? 'Active' : 'Switched off'}
        </span>
      )
    },
    {
      header: 'Action',
      accessor: 'id',
      render: (row) =>
        row.id === me.id ? (
          <span className="text-xs text-slate-400">This is you</span>
        ) : (
          <button
            onClick={() => toggleActive(row)}
            className="px-2.5 py-1 text-xs font-semibold rounded border border-slate-300 hover:bg-slate-100 text-slate-700 transition"
          >
            {row.is_active ? 'Switch off' : 'Switch on'}
          </button>
        )
    },
  ];

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
        <div>
          <h3 className="text-lg font-bold text-slate-900">Staff accounts</h3>
          <p className="text-xs text-slate-500">
            Each role sees only its own screens. Switching an account off signs that person out straight away.
          </p>
        </div>
        <button
          onClick={() => setModalOpen(true)}
          className="inline-flex items-center gap-2 px-3.5 py-2 bg-amber-500 hover:bg-amber-600 text-slate-950 rounded-lg text-sm font-semibold shadow-xs transition"
        >
          <Plus className="w-4 h-4" /> Add staff account
        </button>
      </div>

      <DataTable columns={columns} data={staff} searchPlaceholder="Search staff by name, email or role..." />

      <Modal isOpen={modalOpen} onClose={() => setModalOpen(false)} title="Add a staff account" maxWidth="max-w-md">
        <form onSubmit={handleCreate} className="space-y-4 text-sm">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Full name</label>
            <input maxLength={255}
              required
              minLength={2}
              type="text"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:outline-none"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Email (used to sign in)</label>
            <input maxLength={255}
              required
              type="email"
              value={form.email}
              onChange={(e) => setForm({ ...form, email: e.target.value })}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:outline-none"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Phone (optional)</label>
            <input maxLength={14}
              type="tel"
              pattern="(\+91|91|0)?[ -]?[6-9][0-9]{9}"
              title="Enter a 10 digit mobile number, for example 9876543210"
              value={form.phone}
              onChange={(e) => setForm({ ...form, phone: e.target.value })}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:outline-none"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Role</label>
            <select
              value={form.role}
              onChange={(e) => setForm({ ...form, role: e.target.value, technician_id: '' })}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg bg-white focus:ring-2 focus:ring-amber-500 focus:outline-none"
            >
              {STAFF_ROLE_OPTIONS.map((role) => (
                <option key={role} value={role}>{ROLE_LABELS[role]}</option>
              ))}
            </select>
          </div>
          {form.role === 'technician' && (
            <div>
              <label className="block text-xs font-semibold text-slate-700 mb-1">Technician record</label>
              <select
                value={form.technician_id}
                onChange={(e) => setForm({ ...form, technician_id: e.target.value })}
                className="w-full px-3 py-2 border border-slate-300 rounded-lg bg-white focus:ring-2 focus:ring-amber-500 focus:outline-none"
              >
                <option value="">Create a new technician record</option>
                {freeTechnicians.map((t) => (
                  <option key={t.id} value={t.id}>{t.name} (no login yet)</option>
                ))}
              </select>
            </div>
          )}
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">First password (at least 8 characters)</label>
            <input maxLength={128}
              required
              minLength={8}
              type="password"
              value={form.password} pattern="(?=.*[A-Za-z])(?=.*[0-9]).{8,128}" title="At least 8 characters, with at least one letter and one number"
              onChange={(e) => setForm({ ...form, password: e.target.value })}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:outline-none"
            />
            <p className="text-[11px] text-slate-500 mt-1">They can change it after signing in.</p>
          </div>

          <div className="flex justify-end gap-3 pt-3 border-t border-slate-200">
            <button
              type="button"
              onClick={() => setModalOpen(false)}
              className="px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-100 transition text-xs"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={submitting}
              className="px-4 py-2 bg-amber-500 hover:bg-amber-600 text-slate-950 font-semibold rounded-lg transition text-xs disabled:opacity-50"
            >
              {submitting ? 'Creating...' : 'Create account'}
            </button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
