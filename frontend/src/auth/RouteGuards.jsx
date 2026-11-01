import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from './AuthContext';
import { homeFor, isStaff } from './access';
import { LoadingState } from '../components/States';

// The staff application: needs a sign-in, and a staff role. Customers are sent to the portal.
export function RequireStaff({ children }) {
  const { user, checking } = useAuth();
  if (checking) return <LoadingState message="Checking your sign-in..." />;
  if (!user) return <Navigate to="/login" replace />;
  if (!isStaff(user.role)) return <Navigate to={homeFor(user.role)} replace />;
  return children;
}

// The customer portal: needs a sign-in, and a customer account. Staff are sent to their application.
export function RequireCustomer({ children }) {
  const { user, checking } = useAuth();
  if (checking) return <LoadingState message="Checking your sign-in..." />;
  if (!user) return <Navigate to="/login" replace />;
  if (user.role !== 'customer') return <Navigate to={homeFor(user.role)} replace />;
  return children;
}
