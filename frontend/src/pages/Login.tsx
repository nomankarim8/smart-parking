import { FormEvent, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { CarFront, LockKeyhole, UserRound } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setError('');
    try {
      await login(username, password);
      navigate('/');
    } catch {
      setError('Login failed. Check username/password and backend connection.');
    }
  };

  return (
    <div className="grid min-h-screen place-items-center p-6">
      <div className="grid w-full max-w-5xl overflow-hidden rounded-3xl border border-slate-800 bg-slate-950/80 shadow-2xl lg:grid-cols-2">
        <div className="hidden min-h-[620px] bg-gradient-to-br from-indigo-950 via-slate-950 to-cyan-950 p-10 lg:flex lg:flex-col lg:justify-between">
          <div>
            <div className="flex items-center gap-3">
              <CarFront className="text-indigo-300" />
              <span className="font-black tracking-wider text-white">SMART PARKING</span>
            </div>
            <h1 className="mt-24 text-5xl font-black leading-tight text-white">
              Intelligent parking.<br />
              <span className="text-indigo-300">Recognized automatically.</span>
            </h1>
            <p className="mt-6 max-w-md text-slate-400">
              AI-assisted parking operations with ALPR, smart slot allocation, billing and security monitoring.
            </p>
          </div>
          <div className="text-xs text-slate-600">CSE Final Year Project · AI + Computer Vision + Web Platform</div>
        </div>

        <form onSubmit={submit} className="p-8 sm:p-12">
          <div className="mb-10">
            <div className="mb-3 inline-flex rounded-xl bg-indigo-500/10 p-3 text-indigo-300">
              <LockKeyhole />
            </div>
            <h2 className="text-3xl font-black text-white">Welcome back</h2>
            <p className="mt-2 text-sm text-slate-500">Sign in to the parking control center.</p>
          </div>

          <label htmlFor="username" className="mb-2 block text-xs font-bold uppercase tracking-widest text-slate-500">
            Username
          </label>
          <div className="mb-5 flex items-center gap-2 rounded-xl border border-slate-800 bg-slate-900 px-4">
            <UserRound size={18} className="text-slate-500" />
            <input
              id="username"
              name="username"
              autoComplete="username"
              required
              className="w-full bg-transparent py-3.5 text-white outline-none"
              value={username}
              onChange={event => setUsername(event.target.value)}
            />
          </div>

          <label htmlFor="password" className="mb-2 block text-xs font-bold uppercase tracking-widest text-slate-500">
            Password
          </label>
          <input
            id="password"
            name="password"
            type="password"
            autoComplete="current-password"
            required
            className="mb-6 w-full rounded-xl border border-slate-800 bg-slate-900 px-4 py-3.5 text-white outline-none focus:border-indigo-500"
            value={password}
            onChange={event => setPassword(event.target.value)}
          />

          {error && <div role="alert" className="mb-4 rounded-xl border border-rose-500/20 bg-rose-500/10 p-3 text-sm text-rose-300">{error}</div>}
          <button className="w-full rounded-xl bg-indigo-500 py-3.5 font-bold text-white hover:bg-indigo-400">Sign in</button>
          <p className="mt-6 rounded-xl border border-slate-800 bg-slate-900/50 p-4 text-xs text-slate-500">
            Use the account credentials configured for this installation.
          </p>
        </form>
      </div>
    </div>
  );
}
