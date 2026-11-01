import React from 'react';

const statusStyles = {
  // Positive / Active
  'Approved': 'bg-emerald-50 text-emerald-700 border-emerald-200',
  'Confirmed': 'bg-emerald-50 text-emerald-700 border-emerald-200',
  'Completed': 'bg-emerald-50 text-emerald-700 border-emerald-200',
  'Active': 'bg-emerald-50 text-emerald-700 border-emerald-200',
  'Paid': 'bg-emerald-50 text-emerald-700 border-emerald-200',
  'Resolved': 'bg-emerald-50 text-emerald-700 border-emerald-200',
  'COVERED': 'bg-emerald-100 text-emerald-800 border-emerald-300 font-semibold',
  'Converted': 'bg-emerald-50 text-emerald-700 border-emerald-200',

  // In Progress / Warning
  'Draft': 'bg-slate-100 text-slate-700 border-slate-200',
  'Submitted': 'bg-blue-50 text-blue-700 border-blue-200',
  'Pending Confirmation': 'bg-amber-50 text-amber-700 border-amber-200',
  'Scheduled': 'bg-amber-50 text-amber-700 border-amber-200',
  'In Progress': 'bg-amber-50 text-amber-700 border-amber-200',
  'Open': 'bg-amber-50 text-amber-700 border-amber-200',
  'Assigned': 'bg-indigo-50 text-indigo-700 border-indigo-200',
  'Quotation Sent': 'bg-blue-50 text-blue-700 border-blue-200',
  'Awaiting Dispatch': 'bg-purple-50 text-purple-700 border-purple-200',
  'Customer Confirmed': 'bg-teal-50 text-teal-700 border-teal-200 font-medium',

  // Info
  'Sent': 'bg-blue-50 text-blue-700 border-blue-200',
  'Dispatched': 'bg-purple-50 text-purple-700 border-purple-200',
  'Installed': 'bg-emerald-50 text-emerald-700 border-emerald-200',
  'In Stock': 'bg-sky-50 text-sky-700 border-sky-200',
  'Reserved': 'bg-amber-50 text-amber-700 border-amber-200',

  // Danger / Attention
  'Rejected': 'bg-rose-50 text-rose-700 border-rose-200',
  'Cancelled': 'bg-rose-50 text-rose-700 border-rose-200',
  'Expired': 'bg-rose-50 text-rose-700 border-rose-200',
  'BILLABLE': 'bg-rose-100 text-rose-800 border-rose-300 font-semibold',
  'Urgent': 'bg-rose-100 text-rose-800 border-rose-200 font-bold',
  'Closed': 'bg-slate-100 text-slate-600 border-slate-300',
};

export default function StatusBadge({ status, className = '' }) {
  if (!status) return null;
  const style = statusStyles[status] || 'bg-slate-100 text-slate-700 border-slate-200';

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${style} ${className}`}
    >
      {status}
    </span>
  );
}
