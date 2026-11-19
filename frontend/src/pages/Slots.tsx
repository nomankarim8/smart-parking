import { useEffect, useState } from 'react';
import api from '../services/api';
import type { Slot } from '../types';
import SlotGrid from '../components/SlotGrid';

export default function Slots() {
  const [slots, setSlots] = useState<Slot[]>([]);
  const [loading,setLoading]=useState(true);
  const [error,setError]=useState('');

  const load=()=>{
    setLoading(true);setError('');
    api.get('/slots/',{params:{paginated:true,page:1,page_size:200}})
      .then(r=>setSlots(Array.isArray(r.data)?r.data:r.data.items))
      .catch(()=>setError('Parking slot information could not be loaded.'))
      .finally(()=>setLoading(false));
  };
  useEffect(()=>{load()},[]);

  return (
    <div className="p-4 sm:p-6 lg:p-8">
      
      <div className="mb-7">
        
        <div className="text-xs font-bold uppercase tracking-[.2em] text-emerald-300">
          Parking Infrastructure
        </div>

        <h1 className="text-3xl font-black text-white">
          Parking Slots
        </h1>

      </div>

      {loading&&<div className="glass rounded-2xl p-10 text-center text-slate-400">Loading parking slots…</div>}
      {!loading&&error&&<div className="glass rounded-2xl p-10 text-center"><p className="text-rose-300">{error}</p><button type="button" onClick={load} className="mt-3 rounded-lg border border-slate-700 px-4 py-2 text-sm font-bold">Retry</button></div>}
      {!loading&&!error&&!slots.length&&<div className="glass rounded-2xl p-10 text-center text-slate-500">No parking slot records are configured.</div>}
      {!loading&&!error&&slots.length>0&&<SlotGrid slots={slots} />}

    </div>
  );
}