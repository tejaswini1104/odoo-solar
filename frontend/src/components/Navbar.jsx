import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { KeyRound, LogOut } from 'lucide-react';
import { api } from '../api/client';
import { useAuth } from '../auth/AuthContext';
import { ROLE_LABELS } from '../auth/access';
import Modal from './Modal';
import NotificationBell from './NotificationBell';
import { useToast } from './Toast';

const EMPTY_PASSWORDS = { current_password: '', new_password: '', repeat: '' };

export default function Navbar({ activeTitle, onOpenAlert }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const { addToast } = useToast();
  const [passwordOpen, setPasswordOpen] = useState(false);
  const [passwords, setPasswords] = useState(EMPTY_PASSWORDS);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  const handleLogout = async () => {
    await logout();
    navigate('/login', { replace: true });
  };

  const closePasswordModal = () => {
    setPasswordOpen(false);
    setPasswords(EMPTY_PASSWORDS);
    setError(null);
  };

  const handleChangePassword = async (e) => {
    e.preventDefault();
    setError(null);
    if (passwords.new_password !== passwords.repeat) {
      setError('The new passwords do not match.');
      return;
    }
    try {
      setSaving(true);
      await api.changePassword({
        current_password: passwords.current_password,
        new_password: passwords.new_password,
      });
      addToast('Password changed. Other devices have been signed out.', 'success');
      closePasswordModal();
    } catch (err) {
      setError(err.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <header className="h-16 bg-white border-b border-slate-200 px-8 flex items-center justify-between shrink-0 shadow-xs">
      <div className="flex items-center gap-3">
        <h2 className="text-xl font-bold text-slate-800 capitalize tracking-tight">{activeTitle}</h2>
        <span className="hidden md:inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-amber-50 text-amber-800 border border-amber-200">
          {ROLE_LABELS[user?.role] || user?.role}
        </span>
      </div>

      <div className="flex items-center gap-4 text-xs">
        <NotificationBell onOpen={onOpenAlert} />
        <span className="hidden sm:inline text-slate-600">{user?.email}</span>
        <button
          onClick={() => setPasswordOpen(true)}
          className="inline-flex items-center gap-1.5 font-semibold text-slate-700 hover:text-slate-900"
        >
          <KeyRound className="w-3.5 h-3.5" /> Change password
        </button>
        <button
          onClick={handleLogout}
          className="inline-flex items-center gap-1.5 font-semibold text-slate-700 hover:text-slate-900"
        >
          <LogOut className="w-3.5 h-3.5" /> Sign out
        </button>
      </div>

      <Modal isOpen={passwordOpen} onClose={closePasswordModal} title="Change your password" maxWidth="max-w-md">
        <form onSubmit={handleChangePassword} className="space-y-4 text-sm">
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Current password</label>
            <input maxLength={128}
              required
              type="password"
              value={passwords.current_password}
              onChange={(e) => setPasswords({ ...passwords, current_password: e.target.value })}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:outline-none"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">New password (at least 8 characters)</label>
            <input maxLength={128}
              required
              type="password"
              minLength={8}
              value={passwords.new_password} pattern="(?=.*[A-Za-z])(?=.*[0-9]).{8,128}" title="At least 8 characters, with at least one letter and one number"
              onChange={(e) => setPasswords({ ...passwords, new_password: e.target.value })}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:outline-none"
            />
          </div>
          <div>
            <label className="block text-xs font-semibold text-slate-700 mb-1">Repeat the new password</label>
            <input maxLength={128}
              required
              type="password"
              minLength={8}
              value={passwords.repeat}
              onChange={(e) => setPasswords({ ...passwords, repeat: e.target.value })}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:outline-none"
            />
          </div>

          {error && (
            <div className="text-xs text-rose-700 bg-rose-50 border border-rose-200 rounded-lg p-2.5">{error}</div>
          )}

          <div className="flex justify-end gap-3 pt-2 border-t border-slate-200">
            <button
              type="button"
              onClick={closePasswordModal}
              className="px-4 py-2 border border-slate-300 rounded-lg text-slate-700 hover:bg-slate-100 transition text-xs"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={saving}
              className="px-4 py-2 bg-amber-500 hover:bg-amber-600 text-slate-950 font-semibold rounded-lg transition text-xs disabled:opacity-50"
            >
              {saving ? 'Saving...' : 'Change password'}
            </button>
          </div>
        </form>
      </Modal>
    </header>
  );
}
