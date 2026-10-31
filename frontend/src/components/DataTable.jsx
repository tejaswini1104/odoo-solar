import React, { useState } from 'react';
import { Search } from 'lucide-react';
import { EmptyState } from './States';

export default function DataTable({
  columns,
  data,
  searchPlaceholder = 'Search records...',
  searchField = null,
  emptyTitle = 'No data available',
  emptyDescription = 'There are no records matching your query.',
  actions = null
}) {
  const [searchTerm, setSearchTerm] = useState('');

  const filteredData = React.useMemo(() => {
    if (!searchTerm.trim()) return data;
    const term = searchTerm.toLowerCase();

    return data.filter((item) => {
      if (searchField && item[searchField]) {
        return String(item[searchField]).toLowerCase().includes(term);
      }
      return Object.values(item).some((val) =>
        String(val || '').toLowerCase().includes(term)
      );
    });
  }, [data, searchTerm, searchField]);

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
      {/* Table toolbar */}
      <div className="p-4 border-b border-slate-200 flex flex-col sm:flex-row items-center justify-between gap-3 bg-slate-50/50">
        <div className="relative w-full sm:w-72">
          <Search className="w-4 h-4 absolute left-3 top-3 text-slate-400" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder={searchPlaceholder}
            className="w-full pl-9 pr-4 py-2 border border-slate-300 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-amber-500 focus:border-amber-500"
          />
        </div>
        {actions && <div className="flex items-center gap-2 w-full sm:w-auto">{actions}</div>}
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full text-left text-sm text-slate-700">
          <thead className="bg-slate-100/70 text-xs font-semibold text-slate-600 uppercase tracking-wider border-b border-slate-200">
            <tr>
              {columns.map((col, index) => (
                <th key={index} className={`px-5 py-3.5 ${col.className || ''}`}>
                  {col.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-200">
            {filteredData.length === 0 ? (
              <tr>
                <td colSpan={columns.length} className="p-6">
                  <EmptyState title={emptyTitle} description={emptyDescription} />
                </td>
              </tr>
            ) : (
              filteredData.map((row, rowIndex) => (
                <tr key={rowIndex} className="hover:bg-slate-50/80 transition-colors">
                  {columns.map((col, colIndex) => (
                    <td key={colIndex} className={`px-5 py-3.5 align-middle ${col.cellClassName || ''}`}>
                      {col.render ? col.render(row) : row[col.accessor]}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Footer count */}
      <div className="px-5 py-3 border-t border-slate-200 text-xs text-slate-500 bg-slate-50 flex justify-between items-center">
        <span>Showing {filteredData.length} of {data.length} entries</span>
        {searchTerm && (
          <button
            onClick={() => setSearchTerm('')}
            className="text-amber-600 hover:text-amber-700 font-medium"
          >
            Clear Search
          </button>
        )}
      </div>
    </div>
  );
}
