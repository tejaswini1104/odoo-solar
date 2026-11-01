import React from 'react';
import { Navigate, NavLink, Outlet, useNavigate } from 'react-router-dom';
import { Sun, LogOut } from 'lucide-react';
import { useAuth } from '../auth/AuthContext';
import { LoadingState } from '../components/States';
import NotificationBell from '../components/NotificationBell';

const ALERT_PAGES = { quotes: '/portal/quotations', support: '/portal/support', warranties: '/portal/warranties', invoices: '/portal/invoices' };

const links = [
  { to: '/portal', label: 'Packages', end: true },
  { to: '/portal/enquire', label: 'New Enquiry' },
  { to: '/portal/enquiries', label: 'My Enquiries' },
  { to: '/portal/quotations', label: 'My Quotations' },
  { to: '/portal/payments', label: 'Payments' },
  { to: '/portal/installation', label: 'Installation' },
  { to: '/portal/subsidy', label: 'Subsidy' },
  { to: '/portal/invoices', label: 'Invoices' },
  { to: '/portal/warranties', label: 'Warranties' },
  { to: '/portal/support', label: 'Support' },
];

export default function PortalLayout() {
  const { user, checking, logout } = useAuth();
  const navigate = useNavigate();

  if (checking) return <LoadingState message="Checking your sign-in..." />;
  if (!user) return <Navigate to="/login" replace />;

  const handleLogout = async () => {
    await logout();
    navigate('/login', { replace: true });
  };

  return (
    <div className="min-h-screen bg-slate-100">
      <header className="bg-white border-b border-slate-200 px-6 h-16 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Sun className="w-5 h-5 text-amber-500" />
          <span className="font-bold text-slate-900">SunPower</span>
          <span className="text-xs text-slate-500 hidden sm:inline">Customer portal</span>
        </div>
        <div className="flex items-center gap-4">
          <NotificationBell onOpen={(link) => navigate(ALERT_PAGES[link] || '/portal')} />
          <span className="text-xs text-slate-600 hidden sm:inline">Signed in as {user.name}</span>
          <button
            onClick={handleLogout}
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-slate-700 hover:text-slate-900"
          >
            <LogOut className="w-3.5 h-3.5" /> Sign out
          </button>
        </div>
      </header>

      <nav className="bg-white border-b border-slate-200 px-6 flex gap-6">
        {links.map((link) => (
          <NavLink
            key={link.to}
            to={link.to}
            end={link.end}
            className={({ isActive }) =>
              `py-3 text-sm font-semibold border-b-2 ${
                isActive ? 'border-amber-500 text-slate-900' : 'border-transparent text-slate-500 hover:text-slate-800'
              }`
            }
          >
            {link.label}
          </NavLink>
        ))}
      </nav>

      <main className="max-w-5xl mx-auto p-6">
        <Outlet />
      </main>
    </div>
  );
}
