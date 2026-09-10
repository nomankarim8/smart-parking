import { FormEvent, useEffect, useState } from 'react';
import api from '../services/api';
import type { ALPRResult } from '../types';
import { ScanLine, UploadCloud, Camera as CameraIcon, MapPin, ShieldCheck, AlertTriangle } from 'lucide-react';

type Cam = { camera_id:number; camera_name:string; location:string; camera_role:string; camera_type:string; status:string; stream_url?:string|null };

export default function Entry(){
  const [plate,setPlate]=useState('');
  const [cat,setCat]=useState(2);
  const [alpr,setAlpr]=useState<ALPRResult|null>(null);
  const [busy,setBusy]=useState(false);
  const [msg,setMsg]=useState('');
  const [camera,setCamera]=useState<Cam|null>(null);

  useEffect(()=>{
    api.get('/cameras/').then(r=>setCamera(r.data.find((c:Cam)=>c.camera_role==='ENTRY')||null)).catch(()=>{});
  },[]);

  const scan=async(file:File)=>{
    setBusy(true); setMsg('');
    try{
      const f=new FormData(); f.append('file',file);
      const r=await api.post('/alpr/detect',f);
      const result = r.data as ALPRResult;
      setAlpr(result);
      setPlate(result.normalized_plate || result.license_plate);
      if(result.suggested_category_id){
        setCat(Number(result.suggested_category_id));
      }
      if(result.verification_required){
        setMsg('Manual verification required. Confirm the detected plate before entry.');
      } else {
        setMsg('Plate recognized successfully. Category has been suggested automatically.');
      }
    }catch(e:any){
      setMsg(e?.response?.data?.detail||'ALPR scan failed');
    }finally{setBusy(false)}
  };

  const submit=async(e:FormEvent)=>{
    e.preventDefault(); if(!plate)return;
    setBusy(true);
    try{
      const r=await api.post('/parking/entry',{
        license_plate:plate,
        category_id:cat,
        ocr_confidence:alpr?.confidence||null,
        raw_ocr_text:alpr?.raw_text||null,
        entry_image_url:alpr?.input_image_url||null,
        plate_image_url:alpr?.input_image_url||null,
        camera_id:camera?.camera_id||null
      });
      setMsg(`Entry accepted. Slot ${r.data.slot} assigned to ${r.data.license_plate}.`);
      setAlpr(null);
    }catch(e:any){
      setMsg(e?.response?.data?.detail||'Entry failed');
    }finally{setBusy(false)}
  };

  return <div className="p-4 sm:p-6 lg:p-8">
    <div className="mb-7">
      <div className="text-xs font-bold uppercase tracking-[.2em] text-indigo-300">Gate Workflow</div>
      <h1 className="text-3xl font-black text-white">Vehicle Entry</h1>
      <p className="mt-1 text-sm text-slate-500">Dedicated entry camera → plate detection → Bangla/English OCR → verification → automatic slot assignment</p>
    </div>

    <div className="mb-5 flex flex-wrap items-center gap-3 rounded-2xl border border-sky-400/10 bg-sky-400/5 px-4 py-3">
      <CameraIcon size={18} className="text-sky-300"/>
      <div><div className="text-xs font-bold uppercase tracking-wider text-slate-500">Entry Camera</div><div className="font-bold text-white">{camera?.camera_name||'ENTRY camera not configured'}</div></div>
      {camera&&<div className="ml-auto inline-flex items-center gap-1 text-xs text-slate-500"><MapPin size={13}/>{camera.location}<span className="ml-2 rounded-full bg-emerald-500/10 px-2 py-1 text-emerald-300">{camera.status}</span></div>}
    </div>

    <form onSubmit={submit} className="grid gap-5 xl:grid-cols-2">
      <div className="glass rounded-2xl p-6">
        <div className="mb-4 flex items-center gap-3"><div className="rounded-xl bg-indigo-500/10 p-2 text-indigo-300"><ScanLine/></div><div><h3 className="font-bold text-white">ALPR Scanner</h3><p className="text-xs text-slate-500">Upload a vehicle/plate image captured at the entry gate</p></div></div>
        <label className="mb-2 block text-xs font-bold uppercase tracking-widest text-slate-500">Vehicle image</label>
        <label className="mb-5 flex cursor-pointer flex-col items-center justify-center rounded-2xl border border-dashed border-slate-700 bg-slate-950/50 px-5 py-10 text-center"><UploadCloud className="mb-3 text-slate-500"/><span className="text-sm font-semibold text-slate-300">Click to upload image</span><span className="mt-1 text-xs text-slate-600">Bangla or English plate • JPG/PNG</span><input type="file" accept="image/*" hidden onChange={e=>e.target.files?.[0]&&scan(e.target.files[0])}/></label>

        {alpr&&<div className="space-y-3">
          <div className="rounded-xl border border-indigo-500/20 bg-indigo-500/5 p-4">
            <div className="flex items-center justify-between"><div className="text-xs uppercase tracking-widest text-slate-500">Normalized Plate</div><div className="text-xs font-bold text-indigo-300">{(alpr.confidence*100).toFixed(1)}%</div></div>
            <div className="mt-2 text-2xl font-black text-white">{alpr.normalized_plate||'No plate recognized'}</div>
            <div className="mt-1 text-xs text-slate-500">{alpr.status} • {alpr.detector} • {alpr.ocr_engine||'Manual'}</div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="rounded-xl border border-slate-800 bg-slate-950 p-3"><div className="text-[10px] uppercase tracking-widest text-slate-600">Original OCR</div><div className="mt-1 font-bold text-slate-200">{alpr.raw_text||'—'}</div></div>
            <div className="rounded-xl border border-slate-800 bg-slate-950 p-3"><div className="text-[10px] uppercase tracking-widest text-slate-600">Region</div><div className="mt-1 font-bold text-slate-200">{alpr.region_name||'Unknown'}</div></div>
            <div className="rounded-xl border border-slate-800 bg-slate-950 p-3"><div className="text-[10px] uppercase tracking-widest text-slate-600">Bangla Class</div><div className="mt-1 font-bold text-slate-200">{alpr.class_bn||'—'}</div></div>
            <div className="rounded-xl border border-slate-800 bg-slate-950 p-3"><div className="text-[10px] uppercase tracking-widest text-slate-600">English Class</div><div className="mt-1 font-bold text-indigo-300">{alpr.class_code||'—'}</div></div>
            <div className="rounded-xl border border-slate-800 bg-slate-950 p-3"><div className="text-[10px] uppercase tracking-widest text-slate-600">Series</div><div className="mt-1 font-bold text-slate-200">{alpr.series_number||'—'}</div></div>
            <div className="rounded-xl border border-slate-800 bg-slate-950 p-3"><div className="text-[10px] uppercase tracking-widest text-slate-600">Vehicle No.</div><div className="mt-1 font-bold text-slate-200">{alpr.vehicle_number||'—'}</div></div>
          </div>

          <div className="flex items-center gap-3 rounded-xl border border-slate-800 bg-slate-950 p-4"><div className="rounded-lg bg-emerald-500/10 p-2"><ShieldCheck size={18} className="text-emerald-300"/></div><div><div className="text-xs uppercase tracking-widest text-slate-600">Suggested Vehicle Category</div><div className="mt-1 font-black text-emerald-300">{alpr.vehicle_category||'Manual selection required'}</div></div></div>
        </div>}

        {msg&&<div className="mt-4 flex items-start gap-2 rounded-xl border border-slate-800 bg-slate-950/50 p-3 text-sm text-slate-300"><AlertTriangle size={16} className="mt-0.5 shrink-0 text-amber-300"/>{msg}</div>}
      </div>

      <div className="glass rounded-2xl p-6">
        <h3 className="font-bold text-white">Entry Confirmation</h3>
        <div className="mt-5 space-y-4">
          <div><label className="mb-2 block text-xs font-bold uppercase tracking-widest text-slate-500">License plate</label><input value={plate} onChange={e=>setPlate(e.target.value.toUpperCase())} placeholder="DHAKA METRO GA 12-3456" className="w-full rounded-xl border border-slate-800 bg-slate-950 px-4 py-3.5 font-semibold text-white outline-none focus:border-indigo-500"/></div>
          <div><label className="mb-2 block text-xs font-bold uppercase tracking-widest text-slate-500">Vehicle category</label><select value={cat} onChange={e=>setCat(Number(e.target.value))} className="w-full rounded-xl border border-slate-800 bg-slate-950 px-4 py-3.5 text-white"><option value={1}>Motorcycle</option><option value={2}>Car</option><option value={3}>Van</option><option value={4}>Bus</option><option value={5}>Truck</option></select>{alpr?.suggested_category_id&&<p className="mt-2 text-xs text-indigo-300">Auto-suggested from plate class: {alpr.vehicle_category}</p>}</div>
          <button disabled={busy} className="w-full rounded-xl bg-emerald-500 py-3.5 font-bold text-slate-950 hover:bg-emerald-400 disabled:opacity-50">{busy?'PROCESSING...':'CONFIRM VEHICLE ENTRY'}</button>
        </div>
      </div>
    </form>
  </div>
}
