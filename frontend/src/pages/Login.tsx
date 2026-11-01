import { FormEvent, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  ArrowRight,
  CarFront,
  Check,
  Eye,
  EyeOff,
  LockKeyhole,
  ScanLine,
  ShieldCheck,
  UserRound,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

const highlights = [
  { icon: ScanLine, label: 'Smart vehicle recognition' },
  { icon: ShieldCheck, label: 'Secure operations access' },
];

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState('');

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setError('');
    setIsSubmitting(true);
    try {
      await login(username, password);
      navigate('/');
    } catch {
      setError('Sign-in failed. Check your credentials and connection, then try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <main className="relative isolate min-h-screen overflow-hidden bg-[#050816] text-white">
      <div aria-hidden="true" className="pointer-events-none absolute inset-0 -z-10 overflow-hidden">
        <div className="absolute -left-40 -top-56 h-[36rem] w-[36rem] rounded-full bg-indigo-600/20 blur-[120px]" />
        <div className="absolute -bottom-64 -right-36 h-[34rem] w-[34rem] rounded-full bg-cyan-500/10 blur-[120px]" />
        <div className="absolute inset-0 opacity-[0.12] [background-image:linear-gradient(rgba(148,163,184,.16)_1px,transparent_1px),linear-gradient(90deg,rgba(148,163,184,.16)_1px,transparent_1px)] [background-size:48px_48px] [mask-image:linear-gradient(to_bottom,black,transparent_82%)]" />
      </div>

      <div className="mx-auto flex min-h-screen w-full max-w-[1440px] flex-col px-5 py-5 sm:px-8 sm:py-7 lg:px-12">
        <header className="flex items-center justify-between">
          <a href="/login" aria-label="Smart Parking home" className="inline-flex items-center gap-3 rounded-xl">
            <span className="grid h-11 w-11 place-items-center rounded-2xl border border-indigo-300/20 bg-indigo-400/10 text-indigo-200 shadow-lg shadow-indigo-950/30">
              <CarFront size={23} strokeWidth={2.2} />
            </span>
            <span>
              <span className="block text-sm font-black tracking-[0.16em] text-white">SMART PARKING</span>
              <span className="mt-0.5 block text-[10px] font-semibold uppercase tracking-[0.22em] text-slate-500">Control center</span>
            </span>
          </a>
          <div className="hidden items-center gap-2 rounded-full border border-white/10 bg-white/[0.035] px-3.5 py-2 text-xs font-semibold text-slate-400 sm:inline-flex">
            <span className="relative flex h-2 w-2">
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400/70" />
              <span className="relative inline-flex h-2 w-2 rounded-full bg-emerald-400" />
            </span>
            Secure staff portal
          </div>
        </header>

        <div className="grid flex-1 items-center gap-10 py-10 md:grid-cols-[minmax(0,1fr)_minmax(360px,.95fr)] md:gap-8 lg:grid-cols-[minmax(0,1.05fr)_minmax(420px,.85fr)] lg:gap-16 lg:py-16">
          <section className="mx-auto w-full max-w-2xl lg:mx-0">
            <div className="mb-6 inline-flex items-center gap-2 rounded-full border border-indigo-300/15 bg-indigo-400/[0.07] px-3.5 py-2 text-[11px] font-bold uppercase tracking-[0.16em] text-indigo-200">
              <span className="h-1.5 w-1.5 rounded-full bg-indigo-300" />
              Intelligent parking operations
            </div>
            <h1 className="max-w-2xl text-4xl font-black leading-[1.08] tracking-[-0.045em] text-white sm:text-5xl lg:text-6xl">
              Every arrival,
              <br />
              <span className="bg-gradient-to-r from-indigo-300 via-sky-200 to-cyan-300 bg-clip-text text-transparent">
                under control.
              </span>
            </h1>
            <p className="mt-6 max-w-xl text-base leading-7 text-slate-400 sm:text-lg">
              A clearer view of your parking operation. Sign in to manage entry, spaces, cameras and payments from one place.
            </p>

            <div className="mt-9 grid gap-3 sm:grid-cols-2">
              {highlights.map(({ icon: Icon, label }) => (
                <div key={label} className="flex items-center gap-3 rounded-2xl border border-white/[0.08] bg-white/[0.035] px-4 py-3.5">
                  <span className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-slate-800/80 text-cyan-200">
                    <Icon size={17} />
                  </span>
                  <span className="text-sm font-semibold text-slate-300">{label}</span>
                  <Check className="ml-auto shrink-0 text-emerald-300" size={15} />
                </div>
              ))}
            </div>

            <div className="relative mt-10 hidden max-w-xl overflow-hidden rounded-[1.75rem] border border-white/10 bg-slate-900/60 p-5 shadow-2xl shadow-black/20 md:block">
              <div aria-hidden="true" className="absolute inset-0 bg-gradient-to-br from-indigo-500/[0.09] via-transparent to-cyan-400/[0.06]" />
              <div className="relative flex items-center justify-between gap-5">
                <div>
                  <p className="text-[10px] font-bold uppercase tracking-[0.2em] text-slate-500">One connected workspace</p>
                  <p className="mt-1.5 text-sm font-bold text-white">From the entrance to the final receipt.</p>
                </div>
                <div aria-hidden="true" className="flex -space-x-2">
                  <span className="grid h-10 w-10 place-items-center rounded-xl border border-slate-700 bg-slate-800 text-indigo-200"><CarFront size={18} /></span>
                  <span className="grid h-10 w-10 place-items-center rounded-xl border border-slate-700 bg-slate-800 text-cyan-200"><ScanLine size={17} /></span>
                  <span className="grid h-10 w-10 place-items-center rounded-xl border border-slate-700 bg-slate-800 text-emerald-200"><ShieldCheck size={17} /></span>
                </div>
              </div>
            </div>
          </section>

          <section aria-labelledby="login-heading" className="mx-auto w-full max-w-[480px] lg:ml-auto lg:mr-0">
            <div className="rounded-[2rem] border border-white/[0.12] bg-slate-950/70 p-6 shadow-[0_32px_100px_-35px_rgba(0,0,0,.8)] backdrop-blur-2xl sm:p-9">
              <div className="mb-8">
                <div className="mb-5 grid h-12 w-12 place-items-center rounded-2xl border border-cyan-300/15 bg-cyan-300/[0.08] text-cyan-200">
                  <LockKeyhole size={21} />
                </div>
                <h2 id="login-heading" className="text-2xl font-black tracking-tight text-white sm:text-[1.75rem]">Welcome back</h2>
                <p className="mt-2 text-sm leading-6 text-slate-400">Enter your staff credentials to continue.</p>
              </div>

              <form onSubmit={submit} className="space-y-5">
                <div>
                  <label htmlFor="username" className="mb-2 block text-xs font-bold uppercase tracking-[0.12em] text-slate-300">
                    Username
                  </label>
                  <div className="group flex items-center gap-3 rounded-2xl border border-white/10 bg-slate-900/75 px-4 transition focus-within:border-indigo-400/70 focus-within:ring-4 focus-within:ring-indigo-400/10">
                    <UserRound size={18} className="shrink-0 text-slate-500 transition group-focus-within:text-indigo-300" />
                    <input
                      id="username"
                      name="username"
                      autoComplete="username"
                      autoCapitalize="none"
                      spellCheck={false}
                      required
                      placeholder="Enter your username"
                      className="min-w-0 w-full bg-transparent py-4 text-sm text-white outline-none placeholder:text-slate-600"
                      value={username}
                      onChange={event => setUsername(event.target.value)}
                    />
                  </div>
                </div>

                <div>
                  <div className="mb-2 flex items-center justify-between">
                    <label htmlFor="password" className="block text-xs font-bold uppercase tracking-[0.12em] text-slate-300">
                      Password
                    </label>
                    <span className="inline-flex items-center gap-1 text-[11px] font-medium text-slate-500">
                      <ShieldCheck size={13} />
                      Protected sign-in
                    </span>
                  </div>
                  <div className="group flex items-center gap-3 rounded-2xl border border-white/10 bg-slate-900/75 px-4 transition focus-within:border-indigo-400/70 focus-within:ring-4 focus-within:ring-indigo-400/10">
                    <LockKeyhole size={17} className="shrink-0 text-slate-500 transition group-focus-within:text-indigo-300" />
                    <input
                      id="password"
                      name="password"
                      type={showPassword ? 'text' : 'password'}
                      autoComplete="current-password"
                      required
                      placeholder="Enter your password"
                      className="min-w-0 w-full bg-transparent py-4 text-sm text-white outline-none placeholder:text-slate-600"
                      value={password}
                      onChange={event => setPassword(event.target.value)}
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(value => !value)}
                      aria-label={showPassword ? 'Hide password' : 'Show password'}
                      aria-pressed={showPassword}
                      className="grid h-9 w-9 shrink-0 place-items-center rounded-xl text-slate-500 hover:bg-white/[0.06] hover:text-slate-200"
                    >
                      {showPassword ? <EyeOff size={17} /> : <Eye size={17} />}
                    </button>
                  </div>
                </div>

                {error && (
                  <div role="alert" className="rounded-2xl border border-rose-400/20 bg-rose-400/[0.08] px-4 py-3 text-sm leading-5 text-rose-200">
                    {error}
                  </div>
                )}

                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="group flex w-full items-center justify-center gap-2 rounded-2xl bg-gradient-to-r from-indigo-500 to-blue-500 py-4 text-sm font-extrabold text-white shadow-lg shadow-indigo-950/60 transition hover:-translate-y-0.5 hover:from-indigo-400 hover:to-blue-400 hover:shadow-indigo-950/80 disabled:cursor-wait disabled:opacity-70 disabled:hover:translate-y-0"
                >
                  {isSubmitting ? 'Signing in…' : 'Sign in to your account'}
                  {!isSubmitting && <ArrowRight size={17} className="transition group-hover:translate-x-1" />}
                </button>
              </form>

              <div className="mt-7 flex items-start gap-3 border-t border-white/[0.08] pt-5">
                <ShieldCheck size={16} className="mt-0.5 shrink-0 text-emerald-300" />
                <p className="text-xs leading-5 text-slate-500">
                  Access is limited to authorized staff. Use the account credentials configured for this installation.
                </p>
              </div>
            </div>
            <p className="mt-5 text-center text-[11px] font-medium tracking-wide text-slate-600">
              SMART PARKING <span className="px-1.5 text-slate-700">·</span> OPERATIONS PORTAL
            </p>
          </section>
        </div>
      </div>
    </main>
  );
}
