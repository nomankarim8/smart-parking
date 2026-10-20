import { FormEvent, useCallback, useEffect, useState } from 'react';
import { QRCodeSVG } from 'qrcode.react';
import { CalendarClock, Check, Copy, TicketCheck, X } from 'lucide-react';
import api from '../services/api';
import type { Reservation } from '../types';

type Category = { category_id: number; category_name: string };

function errorMessage(error: unknown) {
  if (typeof error === 'object' && error !== null && 'response' in error) {
    const response = error.response;
    if (typeof response === 'object' && response !== null && 'data' in response) {
      const data = response.data;
      if (typeof data === 'object' && data !== null && 'detail' in data && typeof data.detail === 'string') {
        return data.detail;
      }
    }
  }
  return 'Request failed. Please try again.';
}

export default function Reservations() {
  const [categories, setCategories] = useState<Category[]>([]);
  const [reservations, setReservations] = useState<Reservation[]>([]);
  const [plate, setPlate] = useState('');
  const [categoryId, setCategoryId] = useState('');
  const [issuedPass, setIssuedPass] = useState<Reservation | null>(null);
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);

  const loadData = useCallback(async () => {
    try {
      const [categoryResponse, reservationResponse] = await Promise.all([
        api.get('/reservations/categories'),
        api.get('/reservations/'),
      ]);
      setCategories(categoryResponse.data);
      setReservations(reservationResponse.data);
      setCategoryId((current) => current || String(categoryResponse.data[0]?.category_id ?? ''));
    } catch (error: unknown) {
      setMessage(errorMessage(error));
    }
  }, []);

  useEffect(() => {
    void loadData();
    const timer = window.setInterval(() => void loadData(), 10000);
    return () => window.clearInterval(timer);
  }, [loadData]);

  const createReservation = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setMessage('');
    setIssuedPass(null);
    try {
      const response = await api.post('/reservations/', {
        plate_number: plate.trim(),
        category_id: Number(categoryId),
      });
      setIssuedPass(response.data);
      setPlate('');
      setMessage(`Slot ${response.data.slot} reserved for ${response.data.plate_number}.`);
      await loadData();
    } catch (error: unknown) {
      setMessage(errorMessage(error));
    } finally {
      setBusy(false);
    }
  };

  const cancelReservation = async (reservationId: number) => {
    setMessage('');
    try {
      await api.post(`/reservations/${reservationId}/cancel`);
      setMessage('Reservation cancelled and its slot released.');
      await loadData();
    } catch (error: unknown) {
      setMessage(errorMessage(error));
    }
  };

  const copyToken = async () => {
    if (!issuedPass?.check_in_token) return;
    try {
      await navigator.clipboard.writeText(issuedPass.check_in_token);
      setMessage('Pass token copied.');
    } catch {
      setMessage('Could not copy the token. Select and copy it manually.');
    }
  };

  return (
    <div className="p-4 sm:p-6 lg:p-8">
      <header className="mb-7">
        <div className="text-xs font-bold uppercase tracking-[.2em] text-amber-300">Booking Management</div>
        <h1 className="mt-1 text-3xl font-black text-white">Parking Reservations</h1>
        <p className="mt-1 text-sm text-slate-500">Reserve a matching slot for 30 minutes and issue a one-use QR check-in pass.</p>
      </header>

      <div className="grid gap-5 xl:grid-cols-[.85fr_1.15fr]">
        <section className="glass rounded-2xl p-5 sm:p-6">
          <div className="mb-5 flex items-center gap-3">
            <div className="rounded-xl bg-amber-400/10 p-2 text-amber-300"><CalendarClock /></div>
            <div><h2 className="font-bold text-white">Create reservation</h2><p className="text-xs text-slate-500">The hold expires automatically after 30 minutes.</p></div>
          </div>
          <form onSubmit={createReservation} className="space-y-4">
            <label className="block">
              <span className="mb-2 block text-xs font-bold uppercase tracking-widest text-slate-500">License plate</span>
              <input required minLength={3} maxLength={80} value={plate} onChange={(event) => setPlate(event.target.value.toUpperCase())} placeholder="DHAKA METRO GA 12-3456" className="w-full rounded-xl border border-slate-800 bg-slate-950 px-4 py-3.5 font-semibold text-white outline-none focus:border-indigo-500" />
            </label>
            <label className="block">
              <span className="mb-2 block text-xs font-bold uppercase tracking-widest text-slate-500">Vehicle category</span>
              <select required value={categoryId} onChange={(event) => setCategoryId(event.target.value)} className="w-full rounded-xl border border-slate-800 bg-slate-950 px-4 py-3.5 text-white">
                {categories.map((category) => <option key={category.category_id} value={category.category_id}>{category.category_name}</option>)}
              </select>
            </label>
            <button disabled={busy || !categories.length} className="w-full rounded-xl bg-indigo-500 py-3.5 font-bold text-white hover:bg-indigo-400 disabled:opacity-50">
              {busy ? 'RESERVING…' : 'RESERVE SLOT & ISSUE QR PASS'}
            </button>
          </form>

          {message && <p role="status" className="mt-4 rounded-xl border border-slate-800 bg-slate-950/70 p-3 text-sm text-slate-300">{message}</p>}

          {issuedPass?.check_in_token && <div className="mt-5 rounded-2xl border border-indigo-400/20 bg-indigo-500/5 p-4">
            <div className="mb-3 flex items-center gap-2 font-bold text-white"><TicketCheck size={18} className="text-indigo-300" /> QR check-in pass · {issuedPass.slot}</div>
            <div className="mx-auto w-fit rounded-xl bg-white p-3">
              <QRCodeSVG value={issuedPass.check_in_token} size={200} level="M" />
            </div>
            <p className="mt-3 text-center text-xs text-slate-400">Present this QR at Vehicle Entry before {new Date(issuedPass.expires_at).toLocaleTimeString()}.</p>
            <div className="mt-3 flex gap-2">
              <button type="button" onClick={copyToken} className="flex flex-1 items-center justify-center gap-2 rounded-lg border border-slate-700 px-3 py-2 text-xs font-bold text-slate-200"><Copy size={14} /> Copy pass token</button>
              <a href="/entry" className="flex flex-1 items-center justify-center gap-2 rounded-lg bg-emerald-500/10 px-3 py-2 text-xs font-bold text-emerald-300"><Check size={14} /> Gate check-in</a>
            </div>
            <p className="mt-2 break-all text-center font-mono text-[10px] text-slate-600">{issuedPass.check_in_token}</p>
          </div>}
        </section>

        <section className="glass overflow-hidden rounded-2xl">
          <div className="border-b border-slate-800 p-5">
            <h2 className="font-bold text-white">Recent reservations</h2>
            <p className="mt-1 text-xs text-slate-500">Auto-refreshes every 10 seconds. Only booked reservations can be cancelled.</p>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full min-w-[620px] text-left text-sm">
              <thead className="bg-slate-950/60 text-[10px] uppercase tracking-widest text-slate-500">
                <tr><th className="px-5 py-3">Vehicle</th><th className="px-4 py-3">Slot</th><th className="px-4 py-3">Expires</th><th className="px-4 py-3">Status</th><th className="px-4 py-3">Action</th></tr>
              </thead>
              <tbody className="divide-y divide-slate-800/70">
                {reservations.map((reservation) => <tr key={reservation.reservation_id}>
                  <td className="px-5 py-4"><div className="font-bold text-white">{reservation.plate_number}</div><div className="text-xs text-slate-500">{reservation.category}</div></td>
                  <td className="px-4 py-4 font-semibold text-slate-300">{reservation.slot}</td>
                  <td className="px-4 py-4 text-xs text-slate-400">{new Date(reservation.expires_at).toLocaleString()}</td>
                  <td className="px-4 py-4"><span className={`rounded-full px-2.5 py-1 text-[10px] font-bold ${reservation.status === 'BOOKED' ? 'bg-amber-400/10 text-amber-300' : reservation.status === 'CHECKED_IN' ? 'bg-emerald-400/10 text-emerald-300' : 'bg-slate-700/60 text-slate-400'}`}>{reservation.status.replace('_', ' ')}</span></td>
                  <td className="px-4 py-4">{reservation.status === 'BOOKED' && <button type="button" onClick={() => void cancelReservation(reservation.reservation_id)} className="inline-flex items-center gap-1 rounded-lg border border-rose-400/20 px-2.5 py-1.5 text-xs font-bold text-rose-300 hover:bg-rose-400/10"><X size={13} /> Cancel</button>}</td>
                </tr>)}
                {!reservations.length && <tr><td colSpan={5} className="px-5 py-10 text-center text-sm text-slate-500">No reservations yet.</td></tr>}
              </tbody>
            </table>
          </div>
        </section>
      </div>
    </div>
  );
}
