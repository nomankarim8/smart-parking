import { useCallback, useEffect, useState } from 'react';
import { ClipboardList, RefreshCw } from 'lucide-react';
import api from '../services/api';

type Activity={log_id:number;username:string;action:string;entity_type:string|null;entity_id:number|null;details:Record<string,unknown>;created_at:string};

export default function Audit(){
  const [rows,setRows]=useState<Activity[]>([]);
  const [message,setMessage]=useState('');
  const load=useCallback(async()=>{try{const response=await api.get('/audit/?limit=200');setRows(response.data);setMessage('')}catch{setMessage('Audit history is available to Admin and Super Admin accounts only.')}},[]);
  useEffect(()=>{void load()},[load]);
  return <div className="p-4 sm:p-6 lg:p-8"><header className="mb-7 flex flex-wrap items-end justify-between gap-3"><div><div className="text-xs font-bold uppercase tracking-[.2em] text-violet-300">Administrative History</div><h1 className="mt-1 text-3xl font-black text-white">Audit Log</h1><p className="mt-1 text-sm text-slate-500">Vehicle, camera, fee-rule, reservation, payment and sensor changes.</p></div><button onClick={()=>void load()} className="inline-flex items-center gap-2 rounded-xl border border-slate-700 px-4 py-2.5 text-sm font-bold text-slate-200"><RefreshCw size={15}/> Refresh</button></header>
  {message?<div role="alert" className="rounded-2xl border border-amber-400/20 bg-amber-400/5 p-5 text-sm text-amber-200">{message}</div>:<div className="glass overflow-hidden rounded-2xl"><div className="overflow-x-auto"><table className="w-full min-w-[850px] text-left text-sm"><thead className="bg-slate-950/70 text-xs uppercase tracking-widest text-slate-500"><tr><th className="px-5 py-4">When</th><th>Actor</th><th>Action</th><th>Entity</th><th className="px-5">Details</th></tr></thead><tbody className="divide-y divide-slate-800/70">{rows.map(row=><tr key={row.log_id}><td className="whitespace-nowrap px-5 py-4 text-xs text-slate-500">{new Date(row.created_at).toLocaleString()}</td><td className="font-semibold text-slate-300">{row.username}</td><td><span className="rounded-full bg-violet-400/10 px-2.5 py-1 text-[10px] font-bold text-violet-300">{row.action.replaceAll('_',' ')}</span></td><td className="text-xs text-slate-400">{row.entity_type||'—'}{row.entity_id?` #${row.entity_id}`:''}</td><td className="max-w-lg px-5 py-4"><details><summary className="cursor-pointer text-xs text-indigo-300">View details</summary><pre className="mt-2 whitespace-pre-wrap break-all text-[10px] text-slate-400">{JSON.stringify(row.details,null,2)}</pre></details></td></tr>)}{!rows.length&&<tr><td colSpan={5} className="px-5 py-12 text-center text-slate-500"><ClipboardList className="mx-auto mb-2 opacity-50"/>No audit events recorded yet.</td></tr>}</tbody></table></div></div>}
  </div>;
}
