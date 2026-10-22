import { useCallback, useEffect, useMemo, useState } from 'react';
import { Camera, ChevronLeft, MapPin, RadioTower, RefreshCw, Video } from 'lucide-react';
import { Link } from 'react-router-dom';
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
  if (role === 'ENTRY') return 'Entry gate';
  if (role === 'EXIT') return 'Exit gate';
  return 'Parking zone';
}

function roleClass(role: CameraRole) {
  if (role === 'ENTRY') return 'border-emerald-500/25 bg-emerald-500/10 text-emerald-300';
  if (role === 'EXIT') return 'border-rose-500/25 bg-rose-500/10 text-rose-300';
  return 'border-indigo-500/25 bg-indigo-500/10 text-indigo-300';
}

export default function CameraSidebar() {
  const [cameras, setCameras] = useState<CameraItem[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [collapsed, setCollapsed] = useState(false);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState('');
  const [failedStreamId, setFailedStreamId] = useState<number | null>(null);
  const [streamVersion, setStreamVersion] = useState(0);

  const loadCameras = useCallback(async (manual = false) => {
    if (manual) setRefreshing(true);
    try {
      const response = await api.get<CameraItem[]>('/cameras/');
      setCameras(response.data);
      setSelectedId((current) =>
        response.data.some((camera) => camera.camera_id === current)
          ? current
          : (response.data[0]?.camera_id ?? null),
      );
      setError('');
    } catch (requestError) {
      console.error('Camera sidebar load failed', requestError);
      setError('Camera list could not be loaded. Check your connection and try again.');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    let active = true;
    const load = async () => {
      try {
        const response = await api.get<CameraItem[]>('/cameras/');
        if (active) {
          setCameras(response.data);
          setSelectedId((current) =>
            response.data.some((camera) => camera.camera_id === current)
              ? current
              : (response.data[0]?.camera_id ?? null),
          );
          setError('');
        }
      } catch (requestError) {
        console.error('Camera sidebar load failed', requestError);
        if (active) setError('Camera list could not be loaded. Check your connection and try again.');
      } finally {
        if (active) setLoading(false);
      }
    };
    void load();
    const id = window.setInterval(load, 15000);
    return () => {
      active = false;
      window.clearInterval(id);
    };
  }, []);

  const sorted = useMemo(() => {
    const order: Record<CameraRole, number> = { ENTRY: 1, EXIT: 2, PARKING_ZONE: 3 };
    return [...cameras].sort((a, b) => order[a.camera_role] - order[b.camera_role]);
  }, [cameras]);
  const selectedCamera = sorted.find((camera) => camera.camera_id === selectedId) ?? null;
  const onlineCount = cameras.filter((camera) => camera.status === 'ONLINE').length;
  const token = localStorage.getItem('smart_parking_token') || '';
  const canViewStream = !!selectedCamera && selectedCamera.status === 'ONLINE' && !!selectedCamera.stream_url && !!token;
  const streamUrl = selectedCamera && canViewStream
    ? `${API_BASE}/cameras/${selectedCamera.camera_id}/stream?token=${encodeURIComponent(token)}&v=${streamVersion}`
    : '';
  const streamFailed = !!selectedCamera && failedStreamId === selectedCamera.camera_id;

  const refreshStream = () => {
    setFailedStreamId(null);
    setStreamVersion((version) => version + 1);
  };

  if (collapsed) {
    return (
      <aside className="w-full shrink-0 border-t border-slate-800 bg-slate-950 p-3 xl:sticky xl:top-0 xl:h-screen xl:w-14 xl:border-l xl:border-t-0">
        <div className="flex justify-center xl:pt-3">
          <button
            onClick={() => setCollapsed(false)}
            className="inline-flex items-center gap-2 rounded-xl border border-slate-800 bg-slate-900 p-3 text-slate-300 hover:bg-slate-800"
            title="Open camera panel"
            aria-label="Open camera panel"
          >
            <Camera size={18} />
            <span className="text-xs font-bold xl:hidden">Open camera monitor</span>
          </button>
        </div>
      </aside>
    );
  }

  return (
    <aside className="w-full shrink-0 border-t border-slate-800 bg-slate-950 xl:sticky xl:top-0 xl:h-screen xl:w-[390px] xl:border-l xl:border-t-0">
      <div className="flex h-full min-h-0 flex-col">
        <header className="flex items-center justify-between border-b border-slate-800 px-5 py-4">
          <div>
            <div className="flex items-center gap-2">
              <span className={`h-2.5 w-2.5 rounded-full ${onlineCount ? 'animate-pulse bg-rose-500' : 'bg-slate-600'}`} />
              <h2 className="text-sm font-black tracking-wide text-white">LIVE CAMERA MONITOR</h2>
            </div>
            <p className="mt-1 text-[11px] text-slate-500">
              {onlineCount} of {cameras.length} cameras online
            </p>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => void loadCameras(true)}
              disabled={refreshing}
              className="rounded-lg border border-slate-800 bg-slate-900 p-2 text-slate-400 hover:bg-slate-800 hover:text-white disabled:opacity-50"
              title="Refresh camera list"
              aria-label="Refresh camera list"
            >
              <RefreshCw size={15} className={refreshing ? 'animate-spin' : ''} />
            </button>
            <button
              onClick={() => setCollapsed(true)}
              className="hidden rounded-lg border border-slate-800 bg-slate-900 p-2 text-slate-400 hover:bg-slate-800 xl:block"
              title="Collapse camera panel"
              aria-label="Collapse camera panel"
            >
              <ChevronLeft size={16} />
            </button>
          </div>
        </header>

        <div className="min-h-0 flex-1 space-y-4 overflow-y-auto p-4 sm:p-5 xl:p-4">
          {error && (
            <div role="alert" className="flex items-center justify-between gap-3 rounded-xl border border-rose-500/20 bg-rose-500/10 px-3 py-2.5 text-xs text-rose-300">
              <span>{error}</span>
              <button onClick={() => void loadCameras(true)} className="shrink-0 font-bold underline underline-offset-2">
                Retry
              </button>
            </div>
          )}

          {loading ? (
            <div className="grid aspect-video place-items-center rounded-2xl border border-slate-800 bg-slate-900/60">
              <div className="text-center">
                <RefreshCw className="mx-auto animate-spin text-indigo-300" size={24} />
                <p className="mt-3 text-xs font-semibold text-slate-400">Loading camera feeds…</p>
              </div>
            </div>
          ) : selectedCamera ? (
            <section aria-label="Selected camera feed" className="overflow-hidden rounded-2xl border border-slate-800 bg-slate-900 shadow-xl shadow-black/20">
              <div className="relative aspect-video overflow-hidden bg-slate-950">
                {canViewStream && !streamFailed ? (
                  <img
                    key={`${selectedCamera.camera_id}-${streamVersion}`}
                    src={streamUrl}
                    alt={`${selectedCamera.camera_name} live footage`}
                    className="h-full w-full object-cover"
                    onError={() => setFailedStreamId(selectedCamera.camera_id)}
                    onLoad={() => setFailedStreamId(null)}
                  />
                ) : (
                  <div className="absolute inset-0 grid place-items-center bg-[radial-gradient(ellipse_at_center,_rgba(30,41,59,.8),_rgba(2,6,23,1))] p-5">
                    <div className="text-center">
                      <span className="mx-auto grid h-14 w-14 place-items-center rounded-2xl border border-slate-700 bg-slate-900/80 text-slate-500">
                        {streamFailed ? <RadioTower size={25} /> : <Camera size={25} />}
                      </span>
                      <p className="mt-3 text-xs font-black uppercase tracking-[.14em] text-slate-300">
                        {streamFailed
                          ? 'Feed unavailable'
                          : selectedCamera.status !== 'ONLINE'
                            ? `Camera ${selectedCamera.status.toLowerCase()}`
                            : !selectedCamera.stream_url
                              ? 'No video source configured'
                              : 'Sign in to view live footage'}
                      </p>
                      <p className="mt-1 text-[11px] text-slate-500">
                        {streamFailed ? 'Check the stream source, then retry the feed.' : 'Camera preview will appear here when ready.'}
                      </p>
                      {streamFailed && (
                        <button onClick={refreshStream} className="mt-3 rounded-lg border border-slate-700 bg-slate-800 px-3 py-1.5 text-xs font-bold text-white hover:bg-slate-700">
                          Retry feed
                        </button>
                      )}
                    </div>
                  </div>
                )}
                <div className="pointer-events-none absolute inset-0 bg-gradient-to-t from-black/75 via-transparent to-black/25" />
                <div className="absolute left-3 top-3 flex items-center gap-2">
                  <span className={`inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-[10px] font-black uppercase tracking-wider ${canViewStream && !streamFailed ? 'bg-rose-500 text-white' : 'border border-slate-600 bg-slate-950/80 text-slate-300'}`}>
                    {canViewStream && !streamFailed && <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-white" />}
                    {canViewStream && !streamFailed ? 'Live' : 'Preview'}
                  </span>
                  <span className={`rounded-lg border px-2 py-1 text-[9px] font-black uppercase ${roleClass(selectedCamera.camera_role)}`}>
                    {roleLabel(selectedCamera.camera_role)}
                  </span>
                </div>
                <div className="absolute inset-x-0 bottom-0 flex items-end justify-between gap-3 p-4">
                  <div className="min-w-0">
                    <h3 className="truncate text-base font-black text-white">{selectedCamera.camera_name}</h3>
                    <p className="mt-1 flex items-center gap-1 truncate text-[11px] text-slate-300">
                      <MapPin size={12} className="shrink-0" /> {selectedCamera.location}
                    </p>
                  </div>
                  {canViewStream && (
                    <button
                      onClick={refreshStream}
                      className="shrink-0 rounded-lg border border-white/20 bg-black/40 p-2 text-white backdrop-blur hover:bg-black/60"
                      title="Reconnect to stream"
                      aria-label="Reconnect to stream"
                    >
                      <RefreshCw size={14} />
                    </button>
                  )}
                </div>
              </div>

              <div className="flex items-center justify-between gap-3 px-4 py-3">
                <div className="min-w-0">
                  <p className="text-[9px] font-bold uppercase tracking-[.16em] text-slate-500">Video source</p>
                  <p className="mt-1 truncate text-xs font-semibold text-slate-300">{selectedCamera.camera_type}</p>
                </div>
                <span className={`inline-flex shrink-0 items-center gap-1.5 rounded-full border px-2.5 py-1 text-[10px] font-bold ${selectedCamera.status === 'ONLINE' ? 'border-emerald-500/20 bg-emerald-500/10 text-emerald-300' : 'border-slate-700 bg-slate-800 text-slate-400'}`}>
                  <span className={`h-1.5 w-1.5 rounded-full ${selectedCamera.status === 'ONLINE' ? 'bg-emerald-400' : 'bg-slate-500'}`} />
                  {selectedCamera.status}
                </span>
              </div>
            </section>
          ) : (
            <div className="rounded-2xl border border-dashed border-slate-800 bg-slate-900/50 p-8 text-center">
              <Camera className="mx-auto text-slate-600" size={32} />
              <p className="mt-3 text-sm font-bold text-slate-300">No cameras configured</p>
              <p className="mt-1 text-xs text-slate-500">Add a camera to start monitoring live footage.</p>
              <Link to="/cameras" className="mt-4 inline-flex items-center gap-2 rounded-xl bg-indigo-500/15 px-3 py-2 text-xs font-bold text-indigo-300 hover:bg-indigo-500/25">
                <Video size={14} /> Camera management
              </Link>
            </div>
          )}

          {sorted.length > 0 && (
            <section aria-label="Choose a camera">
              <div className="mb-2 flex items-center justify-between">
                <h3 className="text-[10px] font-black uppercase tracking-[.16em] text-slate-500">All cameras</h3>
                <span className="text-[10px] text-slate-600">Select a feed to preview</span>
              </div>
              <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-1">
                {sorted.map((camera) => {
                  const active = camera.camera_id === selectedCamera?.camera_id;
                  return (
                    <button
                      key={camera.camera_id}
                      type="button"
                      onClick={() => { setSelectedId(camera.camera_id); setFailedStreamId(null); }}
                      aria-pressed={active}
                      className={`flex w-full items-center gap-3 rounded-xl border p-3 text-left ${active ? 'border-indigo-400/40 bg-indigo-500/10 shadow-lg shadow-indigo-950/20' : 'border-slate-800 bg-slate-900/50 hover:border-slate-700 hover:bg-slate-900'}`}
                    >
                      <span className={`grid h-10 w-12 shrink-0 place-items-center rounded-lg border ${camera.status === 'ONLINE' ? 'border-emerald-500/20 bg-emerald-500/10 text-emerald-300' : 'border-slate-700 bg-slate-800 text-slate-500'}`}>
                        <Camera size={17} />
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="flex items-center gap-2">
                          <span className="truncate text-xs font-bold text-white">{camera.camera_name}</span>
                          <span className={`h-1.5 w-1.5 shrink-0 rounded-full ${camera.status === 'ONLINE' ? 'bg-emerald-400' : 'bg-slate-600'}`} />
                        </span>
                        <span className="mt-1 block truncate text-[10px] text-slate-500">{camera.location}</span>
                      </span>
                      <span className={`shrink-0 rounded-md border px-1.5 py-1 text-[8px] font-black uppercase ${roleClass(camera.camera_role)}`}>
                        {roleLabel(camera.camera_role)}
                      </span>
                    </button>
                  );
                })}
              </div>
            </section>
          )}

          <div className="grid grid-cols-2 gap-2">
            <Link to="/monitor" className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-800 bg-slate-900 px-3 py-2.5 text-xs font-bold text-slate-300 hover:border-indigo-500/30 hover:bg-slate-800 hover:text-white">
              <RadioTower size={14} /> CCTV monitor
            </Link>
            <Link to="/cameras" className="inline-flex items-center justify-center gap-2 rounded-xl border border-slate-800 bg-slate-900 px-3 py-2.5 text-xs font-bold text-slate-300 hover:border-indigo-500/30 hover:bg-slate-800 hover:text-white">
              <Video size={14} /> Manage cameras
            </Link>
          </div>
        </div>
      </div>
    </aside>
  );
}
