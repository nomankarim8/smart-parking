import {useEffect,useState} from 'react';
import api from '../services/api';

type Row={record_id:number;plate:string;category:string;slot:string;entry_time:string;exit_time:string|null;status:string};
type PaginatedHistory={items:Row[];total:number;page:number;page_size:number;total_pages:number};

export default function History(){
 const [rows,setRows]=useState<Row[]>([]);
 const [page,setPage]=useState(1);
 const [pageSize,setPageSize]=useState(25);
 const [total,setTotal]=useState(0);
 const [totalPages,setTotalPages]=useState(0);
 const [loading,setLoading]=useState(false);
 const [error,setError]=useState('');
 const [exportError,setExportError]=useState('');

 const load=()=>{
  setLoading(true);setError('');
  api.get('/parking/history',{params:{page,page_size:pageSize,paginated:true}})
   .then(r=>{const data=r.data as PaginatedHistory;setRows(data.items);setTotal(data.total);setTotalPages(data.total_pages)})
   .catch(()=>setError('Parking history could not be loaded.'))
   .finally(()=>setLoading(false));
 };
 useEffect(()=>{void load()},[page,pageSize]);
 const csv=async()=>{
  setExportError('');
  try{
   const r=await api.get('/reports/history.csv',{responseType:'blob'});
   if(!r.data||r.data.size===0){setExportError('The export returned no file data.');return;}
   const url=URL.createObjectURL(r.data);const a=document.createElement('a');a.href=url;a.download='parking_history.csv';a.click();URL.revokeObjectURL(url);
  }catch{setExportError('CSV export failed. The report was not downloaded.');}
 };
 return <div className="p-4 sm:p-6 lg:p-8">
  <div className="mb-7 flex items-end justify-between"><div><div className="text-xs font-bold uppercase tracking-[.2em] text-slate-400">Audit Trail</div><h1 className="text-3xl font-black text-white">Parking History</h1></div><button onClick={()=>void csv()} className="rounded-xl border border-slate-700 px-4 py-2.5 text-sm font-bold text-slate-200 hover:bg-slate-900">Export CSV</button></div>
  {exportError&&<p role="alert" className="mb-4 rounded-xl border border-rose-400/20 bg-rose-400/10 p-3 text-sm text-rose-300">{exportError}</p>}
  <div className="glass overflow-hidden rounded-2xl"><div className="overflow-x-auto"><table className="w-full min-w-[760px] text-left text-sm"><thead className="bg-slate-950/70 text-xs uppercase tracking-widest text-slate-500"><tr><th className="px-5 py-4">ID</th><th>Plate</th><th>Category</th><th>Slot</th><th>Entry</th><th>Exit</th><th>Status</th></tr></thead><tbody className="divide-y divide-slate-800/70">
   {loading&&<tr><td colSpan={7} className="px-5 py-16 text-center text-slate-400">Loading history…</td></tr>}
   {error&&<tr><td colSpan={7} className="px-5 py-16 text-center"><p className="text-rose-300">{error}</p><button onClick={load} className="mt-3 rounded-lg border border-slate-700 px-3 py-2 text-xs font-bold">Retry</button></td></tr>}
   {!loading&&!error&&rows.map(r=><tr key={r.record_id}><td className="px-5 py-4 text-slate-500">#{r.record_id}</td><td className="py-4 font-bold text-indigo-300">{r.plate}</td><td className="py-4 text-slate-400">{r.category}</td><td className="py-4 text-slate-300">{r.slot}</td><td className="py-4 text-slate-500">{new Date(r.entry_time).toLocaleString()}</td><td className="py-4 text-slate-500">{r.exit_time?new Date(r.exit_time).toLocaleString():'—'}</td><td className="py-4"><span className="rounded-full bg-slate-800 px-3 py-1 text-[11px] font-bold text-slate-300">{r.status}</span></td></tr>)}
   {!loading&&!error&&!rows.length&&<tr><td colSpan={7} className="px-5 py-16 text-center text-slate-500">No parking history found.</td></tr>}
  </tbody></table></div>
  <div className="flex flex-col gap-3 border-t border-slate-800 p-4 text-xs text-slate-400 sm:flex-row sm:items-center sm:justify-between"><span>{total?`Showing ${(page-1)*pageSize+1}-${Math.min(page*pageSize,total)} of ${total} records`:'0 records'}</span><div className="flex items-center gap-2"><select value={pageSize} onChange={e=>{setPageSize(Number(e.target.value));setPage(1)}} className="rounded-lg border border-slate-700 bg-slate-950 px-2 py-2"><option value={25}>25 / page</option><option value={50}>50 / page</option><option value={100}>100 / page</option></select><button disabled={page<=1||loading} onClick={()=>setPage(v=>v-1)} className="rounded-lg border border-slate-700 px-3 py-2 disabled:opacity-40">Previous</button><span>Page {page} of {Math.max(totalPages,1)}</span><button disabled={page>=totalPages||loading} onClick={()=>setPage(v=>v+1)} className="rounded-lg border border-slate-700 px-3 py-2 disabled:opacity-40">Next</button></div></div>
  </div>
 </div>
}
