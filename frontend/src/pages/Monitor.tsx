import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { AlertTriangle, Camera, CircleDot, ExternalLink, ScanLine, Video } from 'lucide-react';
import api from '../services/api';
import type { ALPRResult } from '../types';

type CameraItem = {
  camera_id: number;
  camera_name: string;
  location: string;
  camera_role: 'ENTRY'|'EXIT'|'PARKING_ZONE';
  camera_type: string;
  stream_url: string|null;
  status: 'ONLINE'|'OFFLINE'|'UNKNOWN';
};
type ALPRStatus = {
  plate_detector: { status: string };
  vehicle_detector: { status: string; configured: boolean };
  automatic_plate_localization: boolean;
  vehicle_detection: boolean;
};

function CameraFeed({camera}:{camera:CameraItem}){
  const imageRef=useRef<HTMLImageElement|null>(null);
  const [scanning,setScanning]=useState(false);
  const [result,setResult]=useState<ALPRResult|null>(null);
  const [error,setError]=useState('');
  const [streamTicket,setStreamTicket]=useState('');
  const [streamLoaded,setStreamLoaded]=useState(false);
  const [plateOverlay,setPlateOverlay]=useState<{left:number;top:number;width:number;height:number}|null>(null);
  const streamUrl=streamTicket?api.getUri({url:`/cameras/${camera.camera_id}/stream`,params:{ticket:streamTicket}}):'';

  const requestStreamTicket=async()=>{
    const response=await api.post<{ticket:string}>(`/cameras/${camera.camera_id}/stream-ticket`);
    setStreamTicket(response.data.ticket);
    setStreamLoaded(false);
    setError('');
  };

  useEffect(()=>{
    let active=true;
    setStreamTicket('');
    if(camera.status!=='ONLINE'||!camera.stream_url)return;
    api.post<{ticket:string}>(`/cameras/${camera.camera_id}/stream-ticket`)
      .then(response=>{if(active)setStreamTicket(response.data.ticket)})
      .catch(()=>{if(active)setError('Could not authorize this camera feed. Refresh the page or check camera permissions.')});
    return()=>{active=false};
  },[camera.camera_id,camera.status,camera.stream_url]);

  useEffect(()=>{
    const image=imageRef.current;
    const box=result?.plate_box;
    if(!image||!box||box.length!==4||!image.naturalWidth||!image.naturalHeight){
      setPlateOverlay(null);
      return;
    }
    const scale=Math.min(image.clientWidth/image.naturalWidth,image.clientHeight/image.naturalHeight);
    const contentWidth=image.naturalWidth*scale;
    const contentHeight=image.naturalHeight*scale;
    const [x1,y1,x2,y2]=box;
    setPlateOverlay({
      left:(image.offsetLeft+(image.clientWidth-contentWidth)/2+x1*scale),
      top:(image.offsetTop+(image.clientHeight-contentHeight)/2+y1*scale),
      width:Math.max(0,(x2-x1)*scale),
      height:Math.max(0,(y2-y1)*scale),
    });
  },[result,streamLoaded]);

  useEffect(()=>{
    if(!scanning)return;
    let active=true;
    let processing=false;
    const scanFrame=async()=>{
      const image=imageRef.current;
      if(!image||!image.naturalWidth||processing)return;
      processing=true;
      try{
        const canvas=document.createElement('canvas');
        canvas.width=image.naturalWidth;
        canvas.height=image.naturalHeight;
        const context=canvas.getContext('2d');
        if(!context)throw new Error('Could not initialize the frame scanner.');
        context.drawImage(image,0,0);
        const blob=await new Promise<Blob|null>(resolve=>canvas.toBlob(resolve,'image/jpeg',0.82));
        if(!blob)throw new Error('Could not capture a camera frame.');
        const form=new FormData();
        form.append('file',blob,`camera-${camera.camera_id}-frame.jpg`);
        const response=await api.post<ALPRResult>('/alpr/detect?persist=false',form);
        if(active){setResult(response.data);setError('')}
      }catch{
        if(active)setError('Could not scan this frame. Check the camera feed, ALPR model and Bengali/English OCR setup.');
      }finally{processing=false}
    };
    void scanFrame();
    const timer=window.setInterval(()=>void scanFrame(),4000);
    return()=>{active=false;window.clearInterval(timer)};
  },[scanning,camera.camera_id]);

  return <article className="glass min-w-0 overflow-hidden rounded-2xl">
    <div className="flex flex-wrap items-start justify-between gap-3 border-b border-slate-800 p-4">
      <div className="flex min-w-0 items-start gap-3"><span className="rounded-xl bg-indigo-500/10 p-2 text-indigo-300"><Camera size={18}/></span><div className="min-w-0"><h2 className="truncate font-bold text-white">{camera.camera_name}</h2><p className="mt-1 truncate text-xs text-slate-500">{camera.location} · {camera.camera_role.replace('_',' ')}</p></div></div>
      <span className={`inline-flex items-center gap-1 rounded-full px-2.5 py-1 text-[10px] font-bold ${camera.status==='ONLINE'?'bg-emerald-400/10 text-emerald-300':'bg-slate-700/60 text-slate-400'}`}><CircleDot size={11}/>{camera.status}</span>
    </div>
    <div className="relative grid aspect-video min-h-48 place-items-center overflow-hidden bg-slate-950">
      {streamUrl?<img ref={imageRef} crossOrigin="anonymous" src={streamUrl} alt={`${camera.camera_name} live feed`} onLoad={()=>{setStreamLoaded(true);setError('')}} onError={()=>{setStreamLoaded(false);setError('Stream unavailable. Check camera source, server connectivity and camera status.')}} className="h-full w-full object-contain"/>:<div className="p-6 text-center"><Video className="mx-auto mb-3 text-slate-600" size={32}/><p className="text-sm font-semibold text-slate-400">No camera feed configured</p><p className="mt-1 text-xs text-slate-600">Add a stream URL or upload a demo video in Cameras.</p></div>}
      {streamLoaded&&<span className="absolute left-3 top-3 rounded-md bg-black/70 px-2 py-1 text-[10px] font-black tracking-wider text-rose-300">LIVE</span>}
      {scanning&&<span className="absolute right-3 top-3 inline-flex items-center gap-1 rounded-md bg-black/70 px-2 py-1 text-[10px] font-bold text-emerald-300"><ScanLine size={12}/> ALPR SCANNING</span>}
      {streamLoaded&&plateOverlay&&result?.plate_box&&<div className={`pointer-events-none absolute border-2 ${result.verification_required?'border-amber-400':'border-emerald-400'}`} style={{left:plateOverlay.left,top:plateOverlay.top,width:plateOverlay.width,height:plateOverlay.height}}><span className={`absolute -top-6 left-0 max-w-64 truncate px-1.5 py-1 text-[10px] font-black text-white ${result.verification_required?'bg-amber-600':'bg-emerald-600'}`}>{result.normalized_plate||'Plate · verify'} · {(result.confidence*100).toFixed(0)}%</span></div>}
    </div>
    <div className="space-y-3 p-4">
      <div className="flex flex-wrap gap-2"><button type="button" disabled={!streamUrl||camera.status==='OFFLINE'} onClick={()=>{setScanning(value=>!value);setError('')}} className={`inline-flex items-center gap-2 rounded-lg px-3 py-2 text-xs font-bold disabled:cursor-not-allowed disabled:opacity-40 ${scanning?'bg-rose-500/10 text-rose-300':'bg-indigo-500/15 text-indigo-200'}`}><ScanLine size={14}/>{scanning?'Stop ALPR':'Start plate scan'}</button>{(error||!streamLoaded)&&camera.status==='ONLINE'&&camera.stream_url&&<button type="button" onClick={()=>void requestStreamTicket().catch(()=>setError('Could not reconnect to this camera. Check its source and connection.'))} className="inline-flex items-center gap-2 rounded-lg border border-slate-700 px-3 py-2 text-xs font-bold text-slate-200">Reconnect feed</button>}{result?.normalized_plate&&<Link to={`/entry?plate=${encodeURIComponent(result.normalized_plate)}`} className="inline-flex items-center gap-2 rounded-lg border border-slate-700 px-3 py-2 text-xs font-bold text-slate-200"><ExternalLink size={13}/> Use plate at entry</Link>}</div>
      {result&&<div className="rounded-xl border border-slate-800 bg-slate-950/60 p-3"><div className="flex flex-wrap items-center justify-between gap-2"><span className="text-xs text-slate-500">Latest normalized plate</span><span className={`text-[10px] font-bold ${result.verification_required?'text-amber-300':'text-emerald-300'}`}>{result.verification_required?'VERIFY':'AUTO ACCEPTED'} · {(result.confidence*100).toFixed(0)}%</span></div><div className="mt-1 break-words text-lg font-black tracking-wide text-white">{result.normalized_plate||'No plate found'}</div><div className="mt-1 text-[10px] text-slate-500">OCR: {result.ocr_language==='bn'?'Bangla':result.ocr_language==='en'?'English/Latin':'Unclassified'}{result.class_bn?` · Bangla class ${result.class_bn} → ${result.class_code}`:''}</div></div>}
      {error&&<p role="status" className="flex items-start gap-2 text-xs text-amber-300"><AlertTriangle size={14} className="mt-0.5 shrink-0"/>{error}</p>}
    </div>
  </article>;
}

export default function Monitor(){
  const [cameras,setCameras]=useState<CameraItem[]>([]);
  const [error,setError]=useState('');
  const [alprStatus,setAlprStatus]=useState<ALPRStatus|null>(null);
  useEffect(()=>{api.get<CameraItem[]>('/cameras/').then(response=>setCameras(response.data)).catch(()=>setError('Could not load cameras. Please sign in again or check the backend.'));api.get<ALPRStatus>('/alpr/status').then(response=>setAlprStatus(response.data)).catch(()=>setAlprStatus(null))},[]);
  return <div className="min-w-0 p-4 sm:p-6 lg:p-8">
    <header className="mb-7 flex flex-wrap items-end justify-between gap-3"><div><div className="text-xs font-bold uppercase tracking-[.2em] text-emerald-300">Live operations</div><h1 className="mt-1 text-3xl font-black text-white">CCTV Monitor</h1><p className="mt-2 max-w-3xl text-sm text-slate-500">View configured CCTV/RTSP streams or uploaded demo clips. Start ALPR to recognize Bangla or English plates from the live frames.</p></div><Link to="/cameras" className="rounded-xl border border-slate-700 px-4 py-2.5 text-sm font-bold text-slate-200">Manage cameras & video</Link></header>
    {error&&<p role="alert" className="mb-4 rounded-xl border border-rose-400/20 bg-rose-400/5 p-3 text-sm text-rose-300">{error}</p>}
    {alprStatus&&!alprStatus.automatic_plate_localization&&<p role="status" className="mb-4 rounded-xl border border-amber-400/20 bg-amber-400/5 p-3 text-sm text-amber-200">Plate detector model is missing or unavailable. Camera video and OCR/manual review remain available; plate bounding boxes and vehicle detection are not active.</p>}
    {!error&&!cameras.length?<section className="glass rounded-2xl p-10 text-center"><Video className="mx-auto mb-3 text-slate-500" size={36}/><h2 className="font-bold text-white">No cameras configured</h2><p className="mt-2 text-sm text-slate-500">Add a camera or upload a demo video to begin monitoring.</p><Link to="/cameras" className="mt-5 inline-flex rounded-xl bg-indigo-500 px-4 py-2.5 text-sm font-bold text-white">Open camera setup</Link></section>:<div className="grid min-w-0 gap-5 xl:grid-cols-2">{cameras.map(camera=><CameraFeed key={camera.camera_id} camera={camera}/>)}</div>}
  </div>;
}
