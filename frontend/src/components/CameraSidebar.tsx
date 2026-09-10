import { useEffect, useMemo, useState } from 'react';
import { Camera, ChevronLeft, RadioTower } from 'lucide-react';
import api from '../services/api';

type CameraRole = 'ENTRY' | 'EXIT' | 'PARKING_ZONE';
type CameraItem = {
  camera_id: number;
  camera_name: string;
  location: string;
  camera_role: CameraRole;
  camera_type: string;
  stream_url?: string | null;
  status: 'ONLINE' | 'OFFLINE' | 'UNKNOWN';
};

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1';

function roleLabel(role: CameraRole) {
  if (role === 'ENTRY') return 'ENTRY GATE';
  if (role === 'EXIT') return 'EXIT GATE';
  return 'PARKING ZONE';
}

function roleClass(role: CameraRole) {
  if (role === 'ENTRY') return 'border-emerald-500/25 bg-emerald-500/10 text-emerald-300';
  if (role === 'EXIT') return 'border-rose-500/25 bg-rose-500/10 text-rose-300';
  return 'border-indigo-500/25 bg-indigo-500/10 text-indigo-300';
}

export default function CameraSidebar() {
  const [cameras, setCameras] = useState<CameraItem[]>([]);
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    let active = true;
    const load = async () => {
      try {
        const res = await api.get('/cameras/');
        if (active) setCameras(res.data);
      } catch (error) {
        console.error('Camera sidebar load failed', error);
      }
    };
    load();
    const id = window.setInterval(load, 10000);
    return () => {
      active = false;
      window.clearInterval(id);
    };
  }, []);

  const sorted = useMemo(() => {
    const order: Record<CameraRole, number> = { ENTRY: 1, EXIT: 2, PARKING_ZONE: 3 };
    return [...cameras].sort((a, b) => order[a.camera_role] - order[b.camera_role]);
  }, [cameras]);

  const token = localStorage.getItem('smart_parking_token') || '';

  if (collapsed) {
    return (
      <aside className="hidden w-14 shrink-0 border-l border-slate-800 bg-slate-950 xl:block">
        <div className="sticky top-0 flex h-screen items-start justify-center p-3">
          <button
            onClick={() => setCollapsed(false)}
            className="rounded-xl border border-slate-800 bg-slate-900 p-3 text-slate-300 hover:bg-slate-800"
            title="Open camera panel"
          >
            <ChevronLeft size={18} />
          </button>
        </div>
      </aside>
    );
  }

  return (
    <aside className="hidden w-[360px] shrink-0 border-l border-slate-800 bg-slate-950 xl:block">
      <div className="sticky top-0 h-screen">
        <div className="flex items-center justify-between border-b border-slate-800 px-5 py-4">
          <div>
            <div className="flex items-center gap-2">
              <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-rose-500" />
              <h2 className="text-sm font-black tracking-wide text-white">LIVE CAMERAS</h2>
            </div>
            <p className="mt-1 text-[11px] text-slate-500">Entry, exit and parking-zone monitoring</p>
          </div>
          <button
            onClick={() => setCollapsed(true)}
            className="rounded-lg border border-slate-800 bg-slate-900 px-3 py-2 text-xs font-bold text-slate-400 hover:bg-slate-800"
            title="Collapse camera panel"
          >
            <ChevronLeft size={16} />
          </button>
        </div>

        <div className="h-[calc(100vh-78px)] space-y-4 overflow-y-auto p-4">
          {sorted.map((camera) => {
            const online = camera.status === 'ONLINE';
            const hasStream = online && !!camera.stream_url && !!token;
            const streamUrl = `${API_BASE}/cameras/${camera.camera_id}/stream?token=${encodeURIComponent(token)}`;

            return (
              <div key={camera.camera_id} className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900 shadow-lg">
                <div className="flex items-start justify-between gap-3 px-4 py-3">
                  <div className="min-w-0">
                    <div className="truncate text-sm font-black text-white">{camera.camera_name}</div>
                    <div className="mt-0.5 truncate text-[11px] text-slate-500">{camera.location}</div>
                  </div>
                  <span className={`shrink-0 rounded-full border px-2 py-1 text-[9px] font-black ${roleClass(camera.camera_role)}`}>
                    {roleLabel(camera.camera_role)}
                  </span>
                </div>

                <div className="relative aspect-video overflow-hidden bg-black">
                  {hasStream ? (
                    <img src={streamUrl} alt={`${camera.camera_name} live footage`} className="h-full w-full object-cover" />
                  ) : (
                    <div className="flex h-full items-center justify-center">
                      <div className="text-center">
                        <Camera className="mx-auto text-slate-700" size={34} />
                        <div className="mt-3 text-[10px] font-black tracking-widest text-slate-600">
                          {!online ? 'CAMERA OFFLINE' : !camera.stream_url ? 'NO STREAM CONFIGURED' : 'SIGN IN TO VIEW'}
                        </div>
                      </div>
                    </div>
                  )}

                  <div className="absolute left-3 top-3 rounded-lg bg-black/70 px-2 py-1 text-[9px] font-black text-white backdrop-blur">
                    {roleLabel(camera.camera_role)}
                  </div>
                </div>

                <div className="flex items-center justify-between px-4 py-3">
                  <div>
                    <div className="text-[9px] uppercase tracking-widest text-slate-600">Source</div>
                    <div className="mt-1 text-xs font-semibold text-slate-400">{camera.camera_type}</div>
                  </div>
                  <div className="flex items-center gap-2">
                    {camera.status === 'ONLINE' && <RadioTower size={12} className="text-emerald-400" />}
                    <span className={`text-[10px] font-black ${online ? 'text-emerald-400' : 'text-rose-400'}`}>
                      {camera.status}
                    </span>
                  </div>
                </div>
              </div>
            );
          })}

          {sorted.length === 0 && (
            <div className="rounded-2xl border border-dashed border-slate-800 bg-slate-900/50 p-8 text-center">
              <Camera className="mx-auto text-slate-700" size={34} />
              <p className="mt-3 text-sm font-bold text-slate-300">No cameras configured</p>
              <p className="mt-1 text-xs text-slate-600">Add cameras from Camera Management.</p>
            </div>
          )}
        </div>
      </div>
    </aside>
  );
}
