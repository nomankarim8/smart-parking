import { useCallback, useEffect, useState } from 'react';
import { Bell, CheckCheck } from 'lucide-react';
import api from '../services/api';

type NotificationItem = { notification_id:number; title:string; message:string; severity:string; is_read:boolean; created_at:string };

export default function Notifications() {
  const [items, setItems] = useState<NotificationItem[]>([]);
  const [message, setMessage] = useState('');
  const load = useCallback(async () => {
    try { const response = await api.get('/notifications/'); setItems(response.data); }
    catch { setMessage('Could not load notifications. Check your connection and try again.'); }
  }, []);
  useEffect(() => { void load(); const timer=window.setInterval(()=>void load(),10000); return ()=>window.clearInterval(timer); },[load]);
  const markAllRead = async () => { try { await api.post('/notifications/read-all'); await load(); } catch { setMessage('Could not mark notifications as read.'); } };
  const markRead = async (id:number) => { try { await api.post(`/notifications/${id}/read`); await load(); } catch { setMessage('Could not update this notification.'); } };
  const unread=items.filter(item=>!item.is_read).length;
  return <div className="p-4 sm:p-6 lg:p-8">
    <header className="mb-7 flex flex-wrap items-end justify-between gap-3"><div><div className="text-xs font-bold uppercase tracking-[.2em] text-amber-300">System Updates</div><h1 className="mt-1 text-3xl font-black text-white">Notifications</h1><p className="mt-1 text-sm text-slate-500">{unread} unread · refreshes automatically</p></div><button onClick={()=>void markAllRead()} disabled={!unread} className="inline-flex items-center gap-2 rounded-xl border border-slate-700 px-4 py-2.5 text-sm font-bold text-slate-200 disabled:opacity-40"><CheckCheck size={16}/> Mark all read</button></header>
    {message&&<p role="alert" className="mb-4 rounded-xl border border-rose-400/20 bg-rose-400/5 p-3 text-sm text-rose-300">{message}</p>}
    <div className="space-y-3">{items.map(item=><article key={item.notification_id} className={`glass flex items-start gap-4 rounded-2xl border p-4 ${item.is_read?'border-slate-800 opacity-70':'border-indigo-400/20'}`}><div className={`mt-1 rounded-lg p-2 ${item.severity==='WARNING'||item.severity==='CRITICAL'?'bg-amber-400/10 text-amber-300':'bg-indigo-400/10 text-indigo-300'}`}><Bell size={18}/></div><div className="min-w-0 flex-1"><div className="flex flex-wrap items-center gap-2"><h2 className="font-bold text-white">{item.title}</h2><span className="rounded-full bg-slate-800 px-2 py-0.5 text-[10px] font-bold text-slate-400">{item.severity}</span>{!item.is_read&&<span className="h-2 w-2 rounded-full bg-indigo-400"/>}</div><p className="mt-1 text-sm text-slate-300">{item.message}</p><time className="mt-2 block text-xs text-slate-600">{new Date(item.created_at).toLocaleString()}</time></div>{!item.is_read&&<button onClick={()=>void markRead(item.notification_id)} className="shrink-0 rounded-lg border border-slate-700 px-3 py-2 text-xs font-bold text-slate-300">Mark read</button>}</article>)}{!items.length&&!message&&<div className="glass rounded-2xl p-10 text-center text-sm text-slate-500">No notifications yet.</div>}</div>
  </div>;
}
