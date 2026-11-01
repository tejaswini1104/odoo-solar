import React, { useState } from 'react';
import { Link, Navigate, useNavigate } from 'react-router-dom';
import { Sun } from 'lucide-react';
import { useAuth } from './AuthContext';
import { homeFor } from './access';

const EMPTY_FORM = { name: '', email: '', phone: '', password: '', address: '', city: '' };

export default function Register() {
  const { user, checking, register } = useAuth();
  const navigate = useNavigate();
  const [form, setForm] = useState(EMPTY_FORM);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);

  if (checking) return null;
  if (user) return <Navigate to={homeFor(user.role)} replace />;

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    try {
      await register(form);
      navigate('/portal', { replace: true });
    } catch (err) {
      setError(err.message);
    } finally {
      setSubmitting(false);
    }
  };

  const field = (label, key, type = 'text', extra = {}) => (
    <div>
      <label className="block text-xs font-semibold text-slate-700 mb-1">{label}</label>
      <input
        required
        type={type}
        maxLength={255}
        value={form[key]}
        onChange={(e) => setForm({ ...form, [key]: e.target.value })}
        className="w-full px-3 py-2 border border-slate-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:outline-none"
        {...extra}
      />
    </div>
  );

  return (
    <div className="min-h-screen bg-slate-100 flex items-center justify-center p-4">
      <div className="w-full max-w-md bg-white rounded-xl border border-slate-200 shadow-sm p-6">
        <div className="flex items-center gap-2 mb-6">
          <Sun className="w-6 h-6 text-amber-500" />
          <h1 className="text-lg font-bold text-slate-900">Create your customer account</h1>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4 text-sm">
          {field('Full name', 'name', 'text', { minLength: 2 })}
          {field('Email', 'email', 'email')}
          {field('Phone', 'phone', 'tel', { minLength: 10, maxLength: 14, pattern: '(\\+91|91|0)?[ -]?[6-9][0-9]{9}', title: 'Enter a 10 digit mobile number, for example 9876543210' })}
          {field('Password (8+ characters, with a letter and a number)', 'password', 'password', { minLength: 8, maxLength: 128, pattern: '(?=.*[A-Za-z])(?=.*[0-9]).{8,128}', title: 'At least 8 characters, with at least one letter and one number' })}
          {field('Address', 'address', 'text', { minLength: 5 })}
          {field('City', 'city', 'text', { minLength: 2 })}

          {error && (
            <div className="text-xs text-rose-700 bg-rose-50 border border-rose-200 rounded-lg p-2.5">{error}</div>
          )}

          <button
            type="submit"
            disabled={submitting}
            className="w-full px-4 py-2 bg-amber-500 hover:bg-amber-600 text-slate-950 font-semibold rounded-lg transition disabled:opacity-50"
          >
            {submitting ? 'Creating account...' : 'Create account'}
          </button>
        </form>

        <p className="text-xs text-slate-500 mt-5 text-center">
          Already registered?{' '}
          <Link to="/login" className="font-semibold text-amber-700 hover:underline">Sign in</Link>
        </p>
      </div>
    </div>
  );
}
