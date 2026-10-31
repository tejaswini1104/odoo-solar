import React from 'react';
import { Loader2, AlertCircle, FolderOpen, RefreshCw } from 'lucide-react';

export function LoadingState({ message = 'Loading data...' }) {
  return (
    <div className="flex flex-col items-center justify-center p-12 text-slate-500">
      <Loader2 className="w-8 h-8 animate-spin text-amber-500 mb-3" />
      <p className="text-sm font-medium">{message}</p>
    </div>
  );
}

export function EmptyState({
  title = 'No records found',
  description = 'There are no items to display yet.',
  action = null
}) {
  return (
    <div className="flex flex-col items-center justify-center p-12 text-center bg-white rounded-lg border border-dashed border-slate-300">
      <div className="p-3 bg-slate-50 rounded-full mb-3 text-slate-400">
        <FolderOpen className="w-8 h-8" />
      </div>
      <h3 className="text-base font-semibold text-slate-800">{title}</h3>
      <p className="text-sm text-slate-500 max-w-sm mt-1 mb-4">{description}</p>
      {action}
    </div>
  );
}

export function ErrorState({
  title = 'Failed to load data',
  message = 'An unexpected error occurred while communicating with the server.',
  onRetry = null
}) {
  return (
    <div className="flex flex-col items-center justify-center p-8 text-center bg-rose-50 border border-rose-200 rounded-lg text-rose-800">
      <AlertCircle className="w-8 h-8 text-rose-500 mb-2" />
      <h3 className="text-base font-semibold">{title}</h3>
      <p className="text-sm text-rose-600 mt-1 mb-4 max-w-md">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="inline-flex items-center gap-2 px-3 py-1.5 bg-rose-600 text-white rounded-md text-sm font-medium hover:bg-rose-700 transition"
        >
          <RefreshCw className="w-4 h-4" /> Try Again
        </button>
      )}
    </div>
  );
}
