import { FormEvent, useCallback, useEffect, useState } from 'react';
import { Archive, ShieldAlert } from 'lucide-react';
import api from '../services/api';

type BlacklistRow = {
  id: number;
  plate_number: string;
  reason: string;
  notes: string | null;
  is_active: boolean;
  created_at: string;
};

export default function Blacklist() {
  const [rows, setRows] = useState<BlacklistRow[]>([]);
  const [plate, setPlate] = useState('');
  const [reason, setReason] = useState('');
  const [notes, setNotes] = useState('');
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const response = await api.get<BlacklistRow[]>('/blacklist/');
      setRows(response.data);
    } catch {
      setError('Unable to load blacklist entries. Check your access and try again.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const add = async (event: FormEvent) => {
    event.preventDefault();
    setSaving(true);
    setError('');
    setMessage('');
    try {
      await api.post('/blacklist/', { plate_number: plate, reason, notes: notes || null });
      setPlate('');
      setReason('');
      setNotes('');
      setMessage('Blacklist entry saved and audit-logged.');
      await load();
    } catch {
      setError('Unable to save the entry. It may already be active or your role may not allow this action.');
    } finally {
      setSaving(false);
    }
  };

  const deactivate = async (row: BlacklistRow) => {
    if (!window.confirm(`Archive blacklist entry for ${row.plate_number}?`)) return;
    setError('');
    setMessage('');
    try {
      await api.delete(`/blacklist/${row.id}`);
      setMessage('Entry archived; its audit history was retained.');
      await load();
    } catch {
      setError('Unable to archive this entry. Check your role and try again.');
    }
  };

  return (
    <div className="p-4 sm:p-6 lg:p-8">
      <header className="mb-7">
        <div className="text-xs font-bold uppercase tracking-[.2em] text-rose-300">Security Monitoring</div>
        <h1 className="mt-1 flex items-center gap-3 text-3xl font-black text-white"><ShieldAlert className="text-rose-300" /> Blacklist</h1>
        <p className="mt-2 text-sm text-slate-400">Entries are normalized, auditable, and archived instead of physically deleted. Alerts require staff review.</p>
      </header>

      {message && <div role="status" className="mb-4 rounded-xl border border-emerald-400/20 bg-emerald-400/10 p-4 text-sm text-emerald-200">{message}</div>}
      {error && <div role="alert" className="mb-4 rounded-xl border border-rose-400/20 bg-rose-400/10 p-4 text-sm text-rose-200">{error}</div>}

      <div className="grid gap-5 xl:grid-cols-[.8fr_1.2fr]">
        <form onSubmit={add} className="glass rounded-2xl p-6">
          <h2 className="font-bold text-white">Add or reactivate vehicle</h2>
          <label className="mt-5 block text-xs font-bold uppercase tracking-wider text-slate-500">
            Plate number
            <input required minLength={3} maxLength={80} value={plate} onChange={event => setPlate(event.target.value.toUpperCase())} placeholder="Plate number" className="mt-2 w-full rounded-xl border border-slate-800 bg-slate-950 px-4 py-3 text-white outline-none" />
          </label>
          <label className="mt-3 block text-xs font-bold uppercase tracking-wider text-slate-500">
            Reason
            <textarea required maxLength={255} value={reason} onChange={event => setReason(event.target.value)} placeholder="Reason" className="mt-2 min-h-24 w-full rounded-xl border border-slate-800 bg-slate-950 px-4 py-3 text-white outline-none" />
          </label>
          <label className="mt-3 block text-xs font-bold uppercase tracking-wider text-slate-500">
            Notes (optional)
            <textarea maxLength={2000} value={notes} onChange={event => setNotes(event.target.value)} placeholder="Additional review notes" className="mt-2 min-h-20 w-full rounded-xl border border-slate-800 bg-slate-950 px-4 py-3 text-white outline-none" />
          </label>
          <button disabled={saving} className="mt-3 w-full rounded-xl bg-rose-500 py-3 font-bold text-white disabled:opacity-50">{saving ? 'Saving…' : 'Save entry'}</button>
        </form>

        <section className="glass overflow-hidden rounded-2xl">
          <div className="flex items-center justify-between border-b border-white/5 px-5 py-4">
            <h2 className="font-bold text-white">Blacklist history</h2>
            <span className="text-xs text-slate-500">{rows.length} entries</span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[650px] text-left text-sm">
              <thead className="bg-slate-950/70 text-xs uppercase tracking-widest text-slate-500"><tr><th className="px-5 py-4">Plate</th><th>Reason</th><th>Status</th><th>Added</th><th>Action</th></tr></thead>
              <tbody className="divide-y divide-slate-800/70">
                {loading
                  ? <tr><td colSpan={5} className="px-5 py-10 text-center text-slate-500">Loading blacklist…</td></tr>
                  : rows.length === 0
                    ? <tr><td colSpan={5} className="px-5 py-10 text-center text-slate-500">No blacklist entries found.</td></tr>
                    : rows.map(row => (
                      <tr key={row.id}>
                        <td className="px-5 py-4 font-black text-rose-300">{row.plate_number}</td>
                        <td className="py-4 text-slate-400">{row.reason}</td>
                        <td className="py-4 text-xs text-slate-400">{row.is_active ? 'ACTIVE' : 'ARCHIVED'}</td>
                        <td className="py-4 text-xs text-slate-500">{new Date(row.created_at).toLocaleDateString()}</td>
                        <td className="py-4">
                          {row.is_active && <button type="button" onClick={() => void deactivate(row)} className="inline-flex items-center gap-1 rounded-lg border border-white/10 px-2.5 py-1.5 text-xs font-bold text-slate-300 hover:bg-white/5"><Archive size={13} /> Archive</button>}
                        </td>
                      </tr>
                    ))}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </div>
  );
}
