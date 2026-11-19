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
              {items.map((v) => (
                <tr
                  key={v.vehicle_id}
                  className="hover:bg-slate-900/40"
                >
                  <td className="px-5 py-4 font-black text-indigo-300">
                    {v.plate_number}
                  </td>

                  <td className="py-4 text-slate-300">
                    {v.category_id}
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

              {!items.length && (
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
      </div>
    </div>
  );
}