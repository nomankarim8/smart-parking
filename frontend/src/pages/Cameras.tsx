import { useEffect, useMemo, useState } from 'react';
import { Camera, CircleDot, Edit3, MapPin, Plus, Save, Trash2, Video, X } from 'lucide-react';
import api from '../services/api';

type CameraRole = 'ENTRY' | 'EXIT' | 'PARKING_ZONE';
type CameraType = 'USB' | 'IP' | 'RTSP' | 'UPLOAD' | 'DEMO';
type CameraStatus = 'ONLINE' | 'OFFLINE' | 'UNKNOWN';

type CameraItem = {
  camera_id: number;
  camera_name: string;
  location: string;
  camera_role: CameraRole;
  camera_type: CameraType;
  stream_url?: string | null;
  status: CameraStatus;
};

type FormState = {
  camera_name: string;
  location: string;
  camera_role: CameraRole;
  camera_type: CameraType;
  stream_url: string;
  status: CameraStatus;
};

const emptyForm: FormState = {
  camera_name: '',
  location: '',
  camera_role: 'PARKING_ZONE',
  camera_type: 'DEMO',
  stream_url: '',
  status: 'UNKNOWN',
};

const roleMeta: Record<CameraRole, { label: string; icon: string; description: string }> = {
  ENTRY: { label: 'Entry Gate', icon: 'IN', description: 'Vehicle entry + ALPR capture' },
  EXIT: { label: 'Exit Gate', icon: 'OUT', description: 'Exit ALPR + checkout capture' },
  PARKING_ZONE: { label: 'Parking Zone', icon: 'PZ', description: 'Parking-area monitoring' },
};

export default function Cameras() {
  const [cameras, setCameras] = useState<CameraItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');
  const [editing, setEditing] = useState<number | null>(null);
  const [form, setForm] = useState<FormState>(emptyForm);

  const fetchCameras = async () => {
    try {
      const res = await api.get<CameraItem[]>('/cameras/');
      setCameras(res.data);
    } catch (error) {
      setMessage('Unable to load camera configuration.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { fetchCameras(); }, []);

  const summary = useMemo(() => ({
    total: cameras.length,
    online: cameras.filter(c => c.status === 'ONLINE').length,
    entry: cameras.filter(c => c.camera_role === 'ENTRY').length,
    exit: cameras.filter(c => c.camera_role === 'EXIT').length,
    zone: cameras.filter(c => c.camera_role === 'PARKING_ZONE').length,
  }), [cameras]);

  const updateField = <K extends keyof FormState>(key: K, value: FormState[K]) =>
    setForm(prev => ({ ...prev, [key]: value }));

  const startEdit = (camera: CameraItem) => {
    setEditing(camera.camera_id);
    setForm({
      camera_name: camera.camera_name,
      location: camera.location,
      camera_role: camera.camera_role,
      camera_type: camera.camera_type,
      stream_url: camera.stream_url || '',
      status: camera.status,
    });
    setMessage('');
  };

  const resetForm = () => {
    setEditing(null);
    setForm(emptyForm);
  };

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!form.camera_name.trim() || !form.location.trim()) {
      setMessage('Camera name and location are required.');
      return;
    }
    setSaving(true);
    setMessage('');
    try {
      const payload = { ...form, stream_url: form.stream_url.trim() || null };
      if (editing) {
        await api.put(`/cameras/${editing}`, payload);
        setMessage('Camera configuration updated successfully.');
      } else {
        await api.post('/cameras/', payload);
        setMessage('Camera added successfully.');
      }
      resetForm();
      await fetchCameras();
    } catch (error: any) {
      setMessage(error?.response?.data?.detail || 'Camera operation failed.');
    } finally {
      setSaving(false);
    }
  };

  const remove = async (camera: CameraItem) => {
    if (!window.confirm(`Delete ${camera.camera_name}?`)) return;
    try {
      await api.delete(`/cameras/${camera.camera_id}`);
      setMessage('Camera deleted successfully.');
      if (editing === camera.camera_id) resetForm();
      await fetchCameras();
    } catch (error: any) {
      setMessage(error?.response?.data?.detail || 'Unable to delete camera.');
    }
  };

  return (
    <div className="p-4 sm:p-6 lg:p-8">
      <div className="mb-8 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <div className="text-xs font-bold uppercase tracking-[.24em] text-indigo-300">Infrastructure / Cameras</div>
          <h1 className="mt-2 text-3xl font-black text-white sm:text-4xl">Camera Management</h1>
          <p className="mt-2 max-w-3xl text-slate-400">Configure dedicated Entry, Exit and Parking Zone cameras for the ALPR workflow.</p>
        </div>
        <button onClick={resetForm} className="inline-flex items-center justify-center gap-2 rounded-xl border border-white/10 bg-white/5 px-4 py-3 text-sm font-bold text-white hover:bg-white/10">
          <Plus size={18}/> Add Camera
        </button>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
        {[
          ['Total Cameras', summary.total, 'text-white'],
          ['Online', summary.online, 'text-emerald-300'],
          ['Entry', summary.entry, 'text-sky-300'],
          ['Exit', summary.exit, 'text-amber-300'],
          ['Parking Zone', summary.zone, 'text-violet-300'],
        ].map(([label, value, tone]) => (
          <div key={String(label)} className="glass rounded-2xl p-5">
            <div className="text-xs font-bold uppercase tracking-wider text-slate-500">{label}</div>
            <div className={`mt-2 text-3xl font-black ${tone}`}>{value}</div>
          </div>
        ))}
      </div>

      <div className="mt-8 grid gap-6 xl:grid-cols-[1.15fr_1fr]">
        <div className="glass rounded-2xl p-6">
          <div className="mb-5 flex items-center justify-between gap-3">
            <div>
              <h2 className="text-xl font-black text-white">Registered Cameras</h2>
              <p className="mt-1 text-sm text-slate-500">These cameras are available to the parking workflow.</p>
            </div>
            <div className="rounded-xl border border-indigo-400/20 bg-indigo-400/10 px-3 py-2 text-xs font-bold text-indigo-200">ALPR READY</div>
          </div>

          {message && <div className="mb-4 rounded-xl border border-indigo-400/20 bg-indigo-400/10 px-4 py-3 text-sm text-indigo-100">{message}</div>}

          <div className="space-y-3">
            {loading ? <div className="rounded-xl border border-white/5 bg-white/[0.03] p-8 text-center text-slate-500">Loading cameras…</div> : cameras.length === 0 ? <div className="rounded-xl border border-dashed border-white/10 p-10 text-center text-slate-500">No cameras configured yet.</div> : cameras.map(camera => {
              const meta = roleMeta[camera.camera_role];
              return (
                <div key={camera.camera_id} className="rounded-2xl border border-white/5 bg-white/[0.025] p-4 transition hover:bg-white/[0.04]">
                  <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
                    <div className="flex items-start gap-3">
                      <div className="grid size-11 place-items-center rounded-xl bg-indigo-500/10 text-xs font-black text-indigo-200">{meta.icon}</div>
                      <div>
                        <div className="flex flex-wrap items-center gap-2">
                          <h3 className="font-black text-white">{camera.camera_name}</h3>
                          <span className={`rounded-full px-2 py-1 text-[10px] font-black ${camera.status === 'ONLINE' ? 'bg-emerald-400/10 text-emerald-300' : camera.status === 'OFFLINE' ? 'bg-rose-400/10 text-rose-300' : 'bg-white/10 text-slate-400'}`}>{camera.status}</span>
                        </div>
                        <div className="mt-1 flex flex-wrap items-center gap-3 text-xs text-slate-500">
                          <span className="inline-flex items-center gap-1"><MapPin size={13}/>{camera.location}</span>
                          <span className="inline-flex items-center gap-1"><Video size={13}/>{camera.camera_type}</span>
                          <span>{meta.label}</span>
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <button onClick={() => startEdit(camera)} className="inline-flex items-center gap-2 rounded-lg border border-white/10 px-3 py-2 text-xs font-bold text-slate-200 hover:bg-white/5"><Edit3 size={14}/> Edit</button>
                      <button onClick={() => remove(camera)} className="inline-flex items-center gap-2 rounded-lg border border-rose-400/15 px-3 py-2 text-xs font-bold text-rose-300 hover:bg-rose-400/10"><Trash2 size={14}/> Delete</button>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="glass rounded-2xl p-6">
          <div className="mb-5 flex items-center justify-between">
            <div>
              <h2 className="text-xl font-black text-white">{editing ? 'Edit Camera' : 'Add Camera'}</h2>
              <p className="mt-1 text-sm text-slate-500">Assign the camera to the correct parking operation point.</p>
            </div>
            {editing && <button onClick={resetForm} className="rounded-lg p-2 text-slate-400 hover:bg-white/5 hover:text-white"><X size={18}/></button>}
          </div>

          <form onSubmit={submit} className="space-y-4">
            <label className="block"><span className="mb-2 block text-xs font-bold uppercase tracking-wider text-slate-500">Camera Name</span><input value={form.camera_name} onChange={e => updateField('camera_name', e.target.value)} placeholder="ENTRY-01" className="w-full rounded-xl border border-white/10 bg-slate-950/70 px-4 py-3 text-white outline-none focus:border-indigo-400/60" /></label>
            <label className="block"><span className="mb-2 block text-xs font-bold uppercase tracking-wider text-slate-500">Location</span><input value={form.location} onChange={e => updateField('location', e.target.value)} placeholder="Main Entry Gate" className="w-full rounded-xl border border-white/10 bg-slate-950/70 px-4 py-3 text-white outline-none focus:border-indigo-400/60" /></label>

            <div className="grid gap-4 sm:grid-cols-2">
              <label className="block"><span className="mb-2 block text-xs font-bold uppercase tracking-wider text-slate-500">Camera Role</span><select value={form.camera_role} onChange={e => updateField('camera_role', e.target.value as CameraRole)} className="w-full rounded-xl border border-white/10 bg-slate-950/70 px-4 py-3 text-white outline-none"><option value="ENTRY">Entry Gate</option><option value="EXIT">Exit Gate</option><option value="PARKING_ZONE">Parking Zone</option></select></label>
              <label className="block"><span className="mb-2 block text-xs font-bold uppercase tracking-wider text-slate-500">Camera Type</span><select value={form.camera_type} onChange={e => updateField('camera_type', e.target.value as CameraType)} className="w-full rounded-xl border border-white/10 bg-slate-950/70 px-4 py-3 text-white outline-none"><option value="USB">USB Camera</option><option value="IP">IP Camera</option><option value="RTSP">RTSP Stream</option><option value="UPLOAD">Upload Only</option><option value="DEMO">Demo Camera</option></select></label>
            </div>

            <label className="block"><span className="mb-2 block text-xs font-bold uppercase tracking-wider text-slate-500">Stream URL (optional)</span><input value={form.stream_url} onChange={e => updateField('stream_url', e.target.value)} placeholder="rtsp://192.168.1.50:554/stream" className="w-full rounded-xl border border-white/10 bg-slate-950/70 px-4 py-3 font-mono text-sm text-white outline-none focus:border-indigo-400/60" /></label>
            <label className="block"><span className="mb-2 block text-xs font-bold uppercase tracking-wider text-slate-500">Status</span><select value={form.status} onChange={e => updateField('status', e.target.value as CameraStatus)} className="w-full rounded-xl border border-white/10 bg-slate-950/70 px-4 py-3 text-white outline-none"><option value="ONLINE">Online</option><option value="OFFLINE">Offline</option><option value="UNKNOWN">Unknown</option></select></label>

            <div className="rounded-xl border border-white/5 bg-white/[0.025] p-4 text-xs text-slate-500">
              <div className="flex items-center gap-2 font-bold text-slate-300"><CircleDot size={14} />{roleMeta[form.camera_role].label}</div>
              <p className="mt-2">{roleMeta[form.camera_role].description}. This role is used to organize the camera workflow inside the project.</p>
            </div>

            <div className="flex gap-3 pt-2">
              {editing && <button type="button" onClick={resetForm} className="flex-1 rounded-xl border border-white/10 px-4 py-3 font-bold text-slate-300 hover:bg-white/5">Cancel</button>}
              <button disabled={saving} type="submit" className="flex-1 inline-flex items-center justify-center gap-2 rounded-xl bg-indigo-500 px-4 py-3 font-black text-white hover:bg-indigo-400 disabled:opacity-50"><Save size={17}/>{saving ? 'Saving…' : editing ? 'Update Camera' : 'Add Camera'}</button>
            </div>
          </form>
        </div>
      </div>

      <div className="mt-6 grid gap-4 md:grid-cols-3">
        {(['ENTRY','EXIT','PARKING_ZONE'] as CameraRole[]).map(role => {
          const meta = roleMeta[role];
          const camera = cameras.find(c => c.camera_role === role);
          return <div key={role} className="glass rounded-2xl p-5"><div className="flex items-center justify-between"><div className="text-xs font-bold uppercase tracking-widest text-slate-500">{meta.label}</div><span className="rounded-lg bg-white/5 px-2 py-1 text-[10px] font-black text-slate-400">{meta.icon}</span></div><div className="mt-3 text-lg font-black text-white">{camera?.camera_name || 'Not configured'}</div><div className="mt-1 text-xs text-slate-500">{camera?.location || 'Add a dedicated camera for this point.'}</div></div>;
        })}
      </div>
    </div>
  );
}
