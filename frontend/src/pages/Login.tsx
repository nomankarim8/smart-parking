import { FormEvent, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import {
  ArrowRight,
  CarFront,
  Eye,
  EyeOff,
  LockKeyhole,
  ParkingSquare,
  ScanLine,
  ShieldCheck,
  UserRound,
} from 'lucide-react';
import ThemeToggle from '../components/ThemeToggle';
import { useAuth } from '../context/AuthContext';

const highlights = [
  { Icon: ScanLine, label: 'Smart vehicle recognition' },
  { Icon: ShieldCheck, label: 'Secure operations access' },
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
    <main className="login-page relative isolate flex min-h-screen flex-col">
      <header className="mx-auto flex w-full max-w-[1440px] items-center justify-between gap-3 px-4 py-4 sm:px-7 lg:px-10">
        <Link to="/login" aria-label="Smart Parking sign in" className="flex min-h-11 items-center gap-3 rounded-xl">
          <span className="app-brand-mark grid h-11 w-11 place-items-center rounded-xl">
            <ParkingSquare size={22} />
          </span>
          <span>
            <span className="block text-sm font-extrabold tracking-[.12em]">SMART PARKING</span>
            <span className="mt-0.5 block text-[10px] font-semibold uppercase tracking-[.18em] text-muted">Operations center</span>
          </span>
        </Link>
        <ThemeToggle />
      </header>

      <div className="mx-auto grid w-full max-w-[1440px] flex-1 items-center gap-8 px-4 py-6 sm:px-7 md:grid-cols-2 md:gap-10 lg:px-12 lg:py-12">
        <section className="mx-auto w-full max-w-2xl md:mx-0">
          <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-default bg-surface-secondary px-3.5 py-2 text-xs font-bold uppercase tracking-[.12em] text-primary">
            <span className="h-2 w-2 rounded-full bg-primary" />
            Intelligent parking operations
          </div>
          <h1 className="max-w-2xl text-4xl font-extrabold leading-tight tracking-tight sm:text-5xl lg:text-6xl">
            Every arrival,
            <br />
            <span className="text-primary">under control.</span>
          </h1>
          <p className="mt-5 max-w-xl text-base leading-7 text-muted sm:text-lg">
            A clearer view of your parking operation. Sign in to manage entry,
            spaces, cameras and payments from one place.
          </p>

          <div className="mt-7 grid gap-3 sm:grid-cols-2">
            {highlights.map(({ Icon, label }) => (
              <div key={label} className="login-feature flex min-h-14 items-center gap-3 rounded-xl px-4 py-3">
                <span className="app-brand-mark grid h-9 w-9 shrink-0 place-items-center rounded-lg">
                  <Icon size={17} />
                </span>
                <span className="text-sm font-semibold">{label}</span>
              </div>
            ))}
          </div>

          <div className="login-feature mt-7 hidden max-w-xl items-center justify-between gap-4 rounded-2xl p-5 md:flex">
            <div>
              <p className="text-[10px] font-bold uppercase tracking-[.18em] text-muted">One connected workspace</p>
              <p className="mt-1.5 text-sm font-bold">From the entrance to the final receipt.</p>
            </div>
            <div className="flex gap-2" aria-hidden="true">
              <span className="app-brand-mark grid h-10 w-10 place-items-center rounded-xl"><CarFront size={18} /></span>
              <span className="app-brand-mark grid h-10 w-10 place-items-center rounded-xl"><ScanLine size={17} /></span>
              <span className="app-brand-mark grid h-10 w-10 place-items-center rounded-xl"><ShieldCheck size={17} /></span>
            </div>
          </div>
        </section>

        <section aria-labelledby="login-heading" className="mx-auto w-full max-w-[460px] md:ml-auto md:mr-0">
          <div className="login-surface rounded-2xl p-5 sm:p-8">
            <div className="mb-7">
              <div className="app-brand-mark mb-4 grid h-12 w-12 place-items-center rounded-xl">
                <LockKeyhole size={21} />
              </div>
              <h2 id="login-heading" className="text-2xl font-extrabold tracking-tight sm:text-[1.75rem]">Welcome back</h2>
              <p className="mt-2 text-sm leading-6 text-muted">Enter your staff credentials to continue.</p>
            </div>

            <form onSubmit={submit} className="space-y-5">
              <div>
                <label htmlFor="username" className="mb-2 block text-sm font-semibold">Username</label>
                <div className="login-input-group flex min-h-12 items-center gap-3 rounded-xl px-4">
                  <UserRound size={18} className="shrink-0 text-muted" aria-hidden="true" />
                  <input
                    id="username"
                    name="username"
                    autoComplete="username"
                    autoCapitalize="none"
                    autoCorrect="off"
                    required
                    className="login-input w-full text-sm"
                    placeholder="Enter your username"
                    value={username}
                    onChange={event => setUsername(event.target.value)}
                  />
                </div>
              </div>

              <div>
                <label htmlFor="password" className="mb-2 block text-sm font-semibold">Password</label>
                <div className="login-input-group flex min-h-12 items-center gap-3 rounded-xl px-4">
                  <LockKeyhole size={17} className="shrink-0 text-muted" aria-hidden="true" />
                  <input
                    id="password"
                    name="password"
                    type={showPassword ? 'text' : 'password'}
                    autoComplete="current-password"
                    required
                    className="login-input min-w-0 w-full text-sm"
                    placeholder="Enter your password"
                    value={password}
                    onChange={event => setPassword(event.target.value)}
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(value => !value)}
                    aria-label={showPassword ? 'Hide password' : 'Show password'}
                    aria-pressed={showPassword}
                    className="app-quiet-button grid h-10 w-10 shrink-0 place-items-center rounded-lg"
                  >
                    {showPassword ? <EyeOff size={17} /> : <Eye size={17} />}
                  </button>
                </div>
              </div>

              {error && (
                <div role="alert" className="rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-sm leading-5 text-rose-700 dark:text-rose-200">
                  {error}
                </div>
              )}

              <button
                type="submit"
                disabled={isSubmitting}
                className="login-primary flex w-full items-center justify-center gap-2 rounded-xl px-4 text-sm font-bold disabled:opacity-60"
              >
                {isSubmitting ? 'Signing in…' : 'Sign in to your account'}
                {!isSubmitting && <ArrowRight size={17} aria-hidden="true" />}
              </button>
            </form>

            <div className="mt-6 flex items-start gap-3 border-t border-default pt-5">
              <ShieldCheck size={17} className="mt-0.5 shrink-0 text-primary" aria-hidden="true" />
              <p className="text-xs leading-5 text-muted">
                Access is limited to authorized staff. Use the account credentials configured for this installation.
              </p>
            </div>
          </div>
          <p className="mt-4 text-center text-[11px] font-semibold tracking-wide text-muted">
            SMART PARKING <span className="px-1.5">·</span> OPERATIONS PORTAL
          </p>
        </section>
      </div>
    </main>
  );
}
