import { FormEvent, useEffect, useState } from 'react';
import api from '../services/api';
import type { Vehicle } from '../types';
import { Search, Plus, X } from 'lucide-react';

type Category = { category_id:number; category_name:string };
type PaginatedVehicles = { items:Vehicle[]; total:number; page:number; page_size:number; total_pages:number };

function errorDetail(error: unknown, fallback: string) {
  if (typeof error === 'object' && error !== null && 'response' in error) {
    const response = (error as {response?: {data?: {detail?: unknown}}}).response;
    if (typeof response?.data?.detail === 'string') return response.data.detail;
  }
  return fallback;
}

export default function Vehicles() {
  const [items, setItems] = useState<Vehicle[]>([]);
  const [q, setQ] = useState('');
  const [page,setPage]=useState(1);
  const [pageSize,setPageSize]=useState(25);
  const [total,setTotal]=useState(0);
  const [totalPages,setTotalPages]=useState(0);
  const [loading,setLoading]=useState(false);
  const [loadError,setLoadError]=useState('');
  const [open,setOpen]=useState(false);
  const [categories,setCategories]=useState<Category[]>([]);
  const [formError,setFormError]=useState('');
  const [submitting,setSubmitting]=useState(false);
  const [plate,setPlate]=useState('');
  const [categoryId,setCategoryId]=useState('');
  const [ownerName,setOwnerName]=useState('');
  const [ownerPhone,setOwnerPhone]=useState('');
  const [vehicleModel,setVehicleModel]=useState('');
  const [vehicleColor,setVehicleColor]=useState('');

  const load = () => {
    setLoading(true);
    setLoadError('');
    api.get('/vehicles/', {params:{q,page,page_size:pageSize,paginated:true}})
      .then(r=>{
        const data=r.data as PaginatedVehicles;
        setItems(data.items);
        setTotal(data.total);
        setTotalPages(data.total_pages);
        if(data.page>data.total_pages && data.total_pages>0)setPage(data.total_pages);
      })
      .catch(error=>setLoadError(errorDetail(error,'Vehicles could not be loaded. Check your connection and retry.')))
      .finally(()=>setLoading(false));
  };

  useEffect(() => {
    load();
  }, [q,page,pageSize]);

  useEffect(()=>{
    api.get('/vehicles/categories')
      .then(r=>{setCategories(r.data); if(!categoryId) setCategoryId(String(r.data[0]?.category_id||''));})
      .catch(()=>setFormError('Vehicle categories could not be loaded.'));
  },[]);

  const submit=async(event:FormEvent)=>{
    event.preventDefault();
    if(!plate.trim() || !categoryId){setFormError('Plate number and vehicle category are required.');return;}
    setSubmitting(true);setFormError('');
    try{
      await api.post('/vehicles/',{
        plate_number:plate.trim(),
        category_id:Number(categoryId),
        owner_name:ownerName.trim()||null,
        owner_phone:ownerPhone.trim()||null,
        vehicle_model:vehicleModel.trim()||null,
        vehicle_color:vehicleColor.trim()||null,
      });
      setOpen(false);setPlate('');setOwnerName('');setOwnerPhone('');setVehicleModel('');setVehicleColor('');
      setPage(1);load();
    }catch(error){
      setFormError(errorDetail(error,'Vehicle could not be created.'));
    }finally{setSubmitting(false);}
  };

  return (
    <div className="p-4 sm:p-6 lg:p-8">
      <div className="mb-7 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <div className="text-xs font-bold uppercase tracking-[.2em] text-cyan-300">
            Fleet Registry
          </div>

          <h1 className="text-3xl font-black text-white">
            Vehicles
          </h1>
        </div>

        <button type="button" onClick={()=>{setFormError('');setOpen(true)}} className="flex items-center justify-center gap-2 rounded-xl bg-indigo-500 px-4 py-3 text-sm font-bold">
          <Plus size={17} />
          Add Vehicle
        </button>
      </div>

      <div className="glass overflow-hidden rounded-2xl">
        <div className="border-b border-slate-800 p-4">
          <div className="flex items-center gap-3 rounded-xl border border-slate-800 bg-slate-950 px-3">
            <Search size={17} className="text-slate-500" />

            <input
              value={q}
              onChange={(e) => setQ(e.target.value)}
              placeholder="Search plate number..."
              className="w-full bg-transparent py-3 text-white outline-none"
            />
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full min-w-[760px] text-left text-sm">
            <thead className="bg-slate-950/70 text-xs uppercase tracking-widest text-slate-500">
              <tr>
                <th className="px-5 py-4">
                  Plate
                </th>

                <th>
                  Category
                </th>

                <th>
                  Owner
                </th>

                <th>
                  Model
                </th>

                <th>
                  Color
                </th>

                <th>
                  Created
                </th>
              </tr>
            </thead>

            <tbody className="divide-y divide-slate-800/70">
              {loading && (
                <tr><td colSpan={6} className="px-5 py-16 text-center text-slate-400">Loading vehicles…</td></tr>
              )}
              {loadError && (
                <tr><td colSpan={6} className="px-5 py-16 text-center"><p className="text-rose-300">{loadError}</p><button type="button" onClick={load} className="mt-3 rounded-lg border border-slate-700 px-3 py-2 text-xs font-bold text-slate-200">Retry</button></td></tr>
              )}
              {!loading && !loadError && items.map((v) => (
                <tr
                  key={v.vehicle_id}
                  className="hover:bg-slate-900/40"
                >
                  <td className="px-5 py-4 font-black text-indigo-300">
                    {v.plate_number}
                  </td>

                  <td className="py-4 text-slate-300">
                    {categories.find(category=>category.category_id===v.category_id)?.category_name||`Category ${v.category_id}`}
                  </td>

                  <td className="py-4 text-slate-400">
                    {v.owner_name || '—'}
                  </td>

                  <td className="py-4 text-slate-400">
                    {v.vehicle_model || '—'}
                  </td>

                  <td className="py-4 text-slate-400">
                    {v.vehicle_color || '—'}
                  </td>

                  <td className="py-4 text-slate-500">
                    {new Date(v.created_at).toLocaleDateString()}
                  </td>
                </tr>
              ))}

              {!loading && !loadError && !items.length && (
                <tr>
                  <td
                    colSpan={6}
                    className="px-5 py-16 text-center text-slate-600"
                  >
                    No vehicles found
                  </td> 
                </tr>
              )}
            </tbody>
          </table>
        </div>
        <div className="flex flex-col gap-3 border-t border-slate-800 p-4 text-xs text-slate-400 sm:flex-row sm:items-center sm:justify-between">
          <span>{total ? `Showing ${(page-1)*pageSize+1}-${Math.min(page*pageSize,total)} of ${total} vehicles` : '0 vehicles'}</span>
          <div className="flex items-center gap-2">
            <select aria-label="Vehicles per page" value={pageSize} onChange={event=>{setPageSize(Number(event.target.value));setPage(1)}} className="rounded-lg border border-slate-700 bg-slate-950 px-2 py-2">
              {[25,50,100].map(size=><option key={size} value={size}>{size} / page</option>)}
            </select>
            <button type="button" disabled={page<=1||loading} onClick={()=>setPage(value=>value-1)} className="rounded-lg border border-slate-700 px-3 py-2 disabled:opacity-40">Previous</button>
            <span>Page {page} of {Math.max(totalPages,1)}</span>
            <button type="button" disabled={!totalPages||page>=totalPages||loading} onClick={()=>setPage(value=>value+1)} className="rounded-lg border border-slate-700 px-3 py-2 disabled:opacity-40">Next</button>
          </div>
        </div>
      </div>
      {open && (
        <div role="dialog" aria-modal="true" aria-labelledby="add-vehicle-title" className="fixed inset-0 z-[70] grid place-items-center bg-black/70 p-4">
          <form onSubmit={submit} className="w-full max-w-xl rounded-2xl border border-slate-700 bg-slate-950 p-5 shadow-2xl sm:p-6">
            <div className="mb-5 flex items-start justify-between gap-3">
              <div><div className="text-xs font-bold uppercase tracking-wider text-indigo-300">Fleet Registry</div><h2 id="add-vehicle-title" className="mt-1 text-xl font-black text-white">Add Vehicle</h2></div>
              <button type="button" aria-label="Close add vehicle form" onClick={()=>setOpen(false)} className="grid h-10 w-10 place-items-center rounded-lg border border-slate-700 text-slate-400"><X size={18}/></button>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <label className="sm:col-span-2 text-sm text-slate-300"><span className="mb-2 block font-semibold">License plate *</span><input required value={plate} onChange={e=>setPlate(e.target.value.toUpperCase())} className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-3 text-white"/></label>
              <label className="text-sm text-slate-300"><span className="mb-2 block font-semibold">Vehicle category *</span><select required value={categoryId} onChange={e=>setCategoryId(e.target.value)} className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-3 text-white"><option value="">Select category</option>{categories.map(category=><option key={category.category_id} value={category.category_id}>{category.category_name}</option>)}</select></label>
              <label className="text-sm text-slate-300"><span className="mb-2 block font-semibold">Owner name</span><input value={ownerName} onChange={e=>setOwnerName(e.target.value)} className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-3 text-white"/></label>
              <label className="text-sm text-slate-300"><span className="mb-2 block font-semibold">Owner phone</span><input value={ownerPhone} onChange={e=>setOwnerPhone(e.target.value)} className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-3 text-white"/></label>
              <label className="text-sm text-slate-300"><span className="mb-2 block font-semibold">Vehicle model</span><input value={vehicleModel} onChange={e=>setVehicleModel(e.target.value)} className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-3 text-white"/></label>
              <label className="text-sm text-slate-300"><span className="mb-2 block font-semibold">Vehicle color</span><input value={vehicleColor} onChange={e=>setVehicleColor(e.target.value)} className="w-full rounded-xl border border-slate-700 bg-slate-900 px-3 py-3 text-white"/></label>
            </div>
            {formError&&<p role="alert" className="mt-4 rounded-lg border border-rose-400/20 bg-rose-400/10 p-3 text-sm text-rose-300">{formError}</p>}
            <div className="mt-5 flex justify-end gap-3"><button type="button" disabled={submitting} onClick={()=>setOpen(false)} className="rounded-xl border border-slate-700 px-4 py-3 text-sm font-bold text-slate-300">Cancel</button><button type="submit" disabled={submitting||!categories.length} className="rounded-xl bg-indigo-500 px-4 py-3 text-sm font-bold text-white disabled:opacity-50">{submitting?'Creating…':'Create vehicle'}</button></div>
          </form>
        </div>
      )}
    </div>
  );
}