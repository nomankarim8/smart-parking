import { useEffect, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { CheckCircle2, CircleAlert, LoaderCircle, Printer } from 'lucide-react';
import api from '../services/api';

type StatusResponse={payment_status:string;provider:string|null;gateway_status:string|null;receipt:{receipt_number:string;plate_number:string;slot:string;duration_minutes:number;net_amount:number;payment_method:string;transaction_reference:string|null}|null};

export default function PaymentResult(){
  const [params]=useSearchParams();
  const recordId=params.get('record_id');
  const returnResult=params.get('result');
  const [status,setStatus]=useState<StatusResponse|null>(null);
  const [error,setError]=useState('');
  useEffect(()=>{
    if(!recordId){setError('Missing payment reference.');return}
    let active=true;
    const load=async()=>{try{const response=await api.get(`/payments/${recordId}/status`);if(active){setStatus(response.data);setError('')}}catch{if(active)setError('Unable to verify the payment status. Sign in and try again.')}}
    void load();
    const timer=returnResult==='processing'?window.setInterval(()=>void load(),3000):undefined;
    return()=>{active=false;if(timer)window.clearInterval(timer)};
  },[recordId,returnResult]);
  const paid=status?.payment_status==='PAID';
  const processing=returnResult==='processing'&&!paid&&status?.payment_status==='PENDING';
  return <div className="grid min-h-screen place-items-center p-4 sm:p-6"><section className="glass w-full max-w-xl rounded-3xl p-6 text-center sm:p-10">
    {paid?<CheckCircle2 className="mx-auto text-emerald-400" size={48}/>:processing?<LoaderCircle className="mx-auto animate-spin text-sky-300" size={48}/>:<CircleAlert className="mx-auto text-amber-300" size={48}/>}
    <h1 className="mt-5 text-2xl font-black text-white">{paid?'Payment confirmed':processing?'Verifying payment':'Payment not confirmed'}</h1>
    <p className="mt-2 text-sm text-slate-400">{paid?`Verified by ${status?.provider}. Your payment is complete.`:processing?'The gateway response is being verified. This page will update automatically.':'The gateway has not confirmed payment. Check the Payments page before retrying.'}</p>
    {error&&<p role="alert" className="mt-4 text-sm text-rose-300">{error}</p>}
    {status?.receipt&&<div id="payment-result-receipt" className="mt-6 rounded-2xl border border-slate-700 bg-slate-950/50 p-5 text-left font-mono text-sm"><div className="flex justify-between"><span className="text-slate-500">Receipt</span><span>{status.receipt.receipt_number}</span></div><div className="mt-2 flex justify-between"><span className="text-slate-500">Plate</span><span>{status.receipt.plate_number}</span></div><div className="mt-2 flex justify-between"><span className="text-slate-500">Slot</span><span>{status.receipt.slot}</span></div><div className="mt-2 flex justify-between"><span className="text-slate-500">Duration</span><span>{status.receipt.duration_minutes} min</span></div><div className="my-3 border-t border-dashed border-slate-700"/><div className="flex justify-between font-bold"><span>Total paid</span><span className="text-emerald-300">৳{status.receipt.net_amount.toFixed(2)}</span></div><div className="mt-2 text-xs text-emerald-300">PAID · {status.receipt.payment_method}</div></div>}
    <div className="mt-6 flex flex-wrap justify-center gap-3"><Link to="/payments" className="rounded-xl bg-indigo-500 px-5 py-3 text-sm font-bold text-white">Open payments</Link>{paid&&<button onClick={()=>window.print()} className="inline-flex items-center gap-2 rounded-xl border border-slate-700 px-5 py-3 text-sm font-bold text-slate-200"><Printer size={16}/> Print receipt</button>}</div>
  </section></div>;
}
