import React, { useCallback, useEffect, useRef, useState } from 'react';
import { Bell } from 'lucide-react';
import { api } from '../api/client';

const POLL_MS = 30000;

const timeAgo = (iso) => {
  const minutes = Math.max(0, Math.round((Date.now() - new Date(`${iso}Z`).getTime()) / 60000));
  if (minutes < 1) return 'just now';
  if (minutes < 60) return `${minutes} min ago`;
  const hours = Math.round(minutes / 60);
  if (hours < 24) return `${hours} h ago`;
  return `${Math.round(hours / 24)} d ago`;
};

// Alerts for the signed-in person: new enquiries for Sales, jobs for the crew, orders to pack for the warehouse.
// `onOpen(link)` takes them to the screen the alert is about.
export default function NotificationBell({ onOpen }) {
  const [data, setData] = useState({ unread: 0, items: [] });
  const [open, setOpen] = useState(false);
  const box = useRef(null);

  const load = useCallback(async () => {
    try {
      setData(await api.getNotifications());
    } catch {
      // A failed refresh is not worth interrupting anyone for; the next poll tries again
    }
  }, []);

  useEffect(() => {
    load();
    const timer = setInterval(load, POLL_MS);
    return () => clearInterval(timer);
  }, [load]);

  useEffect(() => {
    const close = (e) => { if (box.current && !box.current.contains(e.target)) setOpen(false); };
    document.addEventListener('mousedown', close);
    return () => document.removeEventListener('mousedown', close);
  }, []);

  const openAlert = async (note) => {
    if (!note.is_read) {
      await api.readNotification(note.id).catch(() => {});
      load();
    }
    setOpen(false);
    if (note.link && onOpen) onOpen(note.link);
  };

  const readAll = async () => {
    await api.readAllNotifications().catch(() => {});
    load();
  };

  return (
    <div className="relative" ref={box}>
      <button
        onClick={() => { setOpen(!open); if (!open) load(); }}
        className="relative p-1.5 rounded-lg text-slate-600 hover:bg-slate-100"
        aria-label={`Alerts, ${data.unread} unread`}
      >
        <Bell className="w-4 h-4" />
        {data.unread > 0 && (
          <span className="absolute -top-0.5 -right-0.5 min-w-[16px] h-4 px-1 rounded-full bg-rose-600 text-white text-[10px] font-bold flex items-center justify-center">
            {data.unread > 9 ? '9+' : data.unread}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 mt-2 w-80 bg-white border border-slate-200 rounded-xl shadow-lg z-50 text-left">
          <div className="flex items-center justify-between px-4 py-2.5 border-b border-slate-100">
            <span className="text-xs font-bold text-slate-800">Alerts</span>
            {data.unread > 0 && (
              <button onClick={readAll} className="text-[11px] font-semibold text-amber-700 hover:text-amber-900">Mark all read</button>
            )}
          </div>
          <div className="max-h-96 overflow-y-auto divide-y divide-slate-100">
            {data.items.length === 0 ? (
              <p className="px-4 py-6 text-xs text-slate-500 text-center">Nothing yet. New work and updates appear here.</p>
            ) : (
              data.items.map((note) => (
                <button
                  key={note.id}
                  onClick={() => openAlert(note)}
                  className={`w-full text-left px-4 py-2.5 hover:bg-slate-50 ${note.is_read ? '' : 'bg-amber-50/60'}`}
                >
                  <div className="flex items-start gap-2">
                    {!note.is_read && <span className="mt-1.5 w-1.5 h-1.5 rounded-full bg-rose-600 shrink-0" />}
                    <div className="min-w-0">
                      <p className="text-xs font-semibold text-slate-900">{note.title}</p>
                      {note.body && <p className="text-[11px] text-slate-600 mt-0.5">{note.body}</p>}
                      <p className="text-[10px] text-slate-400 mt-1">{timeAgo(note.created_at)}</p>
                    </div>
                  </div>
                </button>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
}
