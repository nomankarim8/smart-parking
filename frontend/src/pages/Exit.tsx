import { FormEvent, useEffect, useState } from 'react';
import { Camera as CameraIcon, MapPin, Printer, ReceiptText } from 'lucide-react';
import api from '../services/api';
import type { ExitResult } from '../types';

type Cam = { camera_id:number; camera_name:string; location:string; camera_role:string };
type Receipt = ExitResult & { receipt_number?:string; payment_id?:number; transaction_reference?:string|null; payment_time?:string|null };

function errorMessage(error: unknown) {
  if (typeof error === 'object' && error !== null && 'response' in error) {
    const response = error.response;
    if (typeof response === 'object' && response !== null && 'data' in response) {
      const data = response.data;
      if (typeof data === 'object' && data !== null && 'detail' in data && typeof data.detail === 'string') return data.detail;
    }
  }
  return 'Request failed. Please try again.';
}

export default function Exit() {
  const [plate, setPlate] = useState('');
  const [method, setMethod] = useState('CASH');
  const [result, setResult] = useState<Receipt | null>(null);
  const [msg, setMsg] = useState('');
  const [camera, setCamera] = useState<Cam | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.get('/cameras/').then((response) => setCamera(response.data.find((item: Cam) => item.camera_role === 'EXIT') || null)).catch(() => setCamera(null));
  }, []);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setBusy(true);
    setMsg('');
    try {
      const response = await api.post('/parking/exit', { license_plate:plate, payment_method:method, camera_id:camera?.camera_id || null });
      setResult(response.data);
      setMsg('Exit completed. Slot released; payment is pending until demo payment is completed.');
    } catch (error: unknown) {
      setMsg(errorMessage(error));
    } finally {
      setBusy(false);
    }
  };

  const processDemoPayment = async (outcome:'APPROVED'|'DECLINED') => {
    if (!result) return;
    setBusy(true);
    setMsg('');
    try {
      const response = await api.post(`/payments/${result.record_id}/demo`, { outcome });
      setResult(response.data);
      setMsg(outcome === 'APPROVED' ? 'Demo payment approved. Receipt is ready.' : 'Demo payment declined. Amount remains due; you can retry.');
    } catch (error: unknown) {
      setMsg(errorMessage(error));
    } finally {
      setBusy(false);
    }
  };

  return <div className="p-4 sm:p-6 lg:p-8">
    <div className="mb-7"><div className="text-xs font-bold uppercase tracking-[.2em] text-rose-300">Checkout Workflow</div><h1 className="text-3xl font-black text-white">Vehicle Exit & Payment</h1><p className="mt-1 text-sm text-slate-500">Complete exit, release the slot, then simulate payment approval or decline.</p></div>
    <div className="mb-5 flex flex-wrap items-center gap-3 rounded-2xl border border-amber-400/10 bg-amber-400/5 px-4 py-3"><CameraIcon size={18} className="text-amber-300"/><div><div className="text-xs font-bold uppercase tracking-wider text-slate-500">Exit Camera</div><div className="font-bold text-white">{camera?.camera_name||'EXIT camera not configured'}</div></div>{camera&&<div className="ml-auto inline-flex items-center gap-1 text-xs text-slate-500"><MapPin size={13}/>{camera.location}</div>}</div>
    <div className="grid gap-5 xl:grid-cols-[.9fr_1.1fr]">
      <form onSubmit={submit} className="glass rounded-2xl p-6">
        <h3 className="font-bold text-white">Checkout</h3>
        <label className="mt-5 mb-2 block text-xs font-bold uppercase tracking-widest text-slate-500">License plate</label>
        <input required minLength={3} value={plate} onChange={event=>setPlate(event.target.value.toUpperCase())} placeholder="DHAKA METRO GA 12-3456" className="w-full rounded-xl border border-slate-800 bg-slate-950 px-4 py-3.5 font-semibold text-white outline-none focus:border-rose-500"/>
        <label className="mt-5 mb-2 block text-xs font-bold uppercase tracking-widest text-slate-500">Payment method</label>
        <select value={method} onChange={event=>setMethod(event.target.value)} className="w-full rounded-xl border border-slate-800 bg-slate-950 px-4 py-3.5 text-white"><option>CASH</option><option>CARD</option><option>MOBILE_BANKING</option><option>ONLINE</option></select>
        <button disabled={busy} className="mt-6 w-full rounded-xl bg-rose-500 py-3.5 font-bold text-white hover:bg-rose-400 disabled:opacity-50">{busy?'PROCESSING…':'CALCULATE & COMPLETE EXIT'}</button>
        {msg&&<div role="status" className="mt-4 rounded-xl border border-slate-700 bg-slate-950/70 p-3 text-sm text-slate-300">{msg}</div>}
      </form>
      <div className="glass rounded-2xl p-6">
        <div className="mb-5 flex items-center gap-3"><ReceiptText className="text-indigo-300"/><div><h3 className="font-bold text-white">Digital Receipt</h3><p className="text-xs text-slate-500">Demo transaction status and printable receipt</p></div></div>
        {result?<div id="parking-receipt" className="rounded-2xl border border-slate-800 bg-slate-950/60 p-5 font-mono">
          <div className="flex justify-between py-2 text-sm"><span className="text-slate-500">Receipt</span><span>{result.receipt_number||`#${result.record_id}`}</span></div>
          <div className="flex justify-between py-2 text-sm"><span className="text-slate-500">Plate</span><span>{result.license_plate}</span></div>
          <div className="flex justify-between py-2 text-sm"><span className="text-slate-500">Slot</span><span>{result.slot}</span></div>
          <div className="flex justify-between py-2 text-sm"><span className="text-slate-500">Duration</span><span>{result.duration_minutes} min</span></div>
          <div className="my-3 border-t border-dashed border-slate-800"/>
          <div className="flex justify-between py-1 text-sm"><span className="text-slate-500">Gross</span><span>৳{result.gross_amount.toFixed(2)}</span></div>
          <div className="flex justify-between py-1 text-sm"><span className="text-slate-500">Discount</span><span>৳{result.discount_amount.toFixed(2)}</span></div>
          <div className="mt-2 flex justify-between text-lg font-black"><span>Total</span><span className="text-emerald-300">৳{result.net_amount.toFixed(2)}</span></div>
          <div className="mt-3 text-xs text-slate-400">Payment: {result.payment_method} • <span className={result.payment_status==='PAID'?'text-emerald-300':result.payment_status==='FAILED'?'text-rose-300':'text-amber-300'}>{result.payment_status}</span></div>
          {result.transaction_reference&&<div className="mt-2 break-all text-[11px] text-slate-500">Reference: {result.transaction_reference}</div>}
          {result.payment_status!=='PAID'&&<div className="mt-4 grid gap-2 sm:grid-cols-2">
            <button disabled={busy} onClick={()=>void processDemoPayment('APPROVED')} className="rounded-lg bg-emerald-500 px-3 py-2 text-xs font-bold text-slate-950 disabled:opacity-50">DEMO APPROVE PAYMENT</button>
            <button disabled={busy} onClick={()=>void processDemoPayment('DECLINED')} className="rounded-lg border border-rose-400/30 px-3 py-2 text-xs font-bold text-rose-300 disabled:opacity-50">DEMO DECLINE</button>
          </div>}
          {result.payment_status==='PAID'&&<button onClick={()=>window.print()} className="mt-4 inline-flex items-center gap-2 rounded-lg border border-slate-700 px-3 py-2 text-xs font-bold text-slate-200"><Printer size={14}/> Print receipt</button>}
        </div>:<div className="grid h-56 place-items-center rounded-2xl border border-dashed border-slate-800 text-sm text-slate-600">No checkout generated yet</div>}
      </div>
    </div>
  </div>;
}
