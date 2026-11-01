import { FormEvent, useState } from 'react';
import { useAuth } from '../context/AuthContext';
import { KeyRound, LogOut, ShieldCheck } from 'lucide-react';
import ThemeToggle from '../components/ThemeToggle';

export default function PasswordRotation() {
  const { changePassword, logout, user } = useAuth();
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmation, setConfirmation] = useState('');
  const [error, setError] = useState('');
  const [saving, setSaving] = useState(false);

  const submit = async (event: FormEvent) => {
    event.preventDefault();
    setError('');
    if (newPassword !== confirmation) {
      setError('The new passwords do not match.');
      return;
    }
    setSaving(true);
    try {
      await changePassword(currentPassword, newPassword);
    } catch (requestError) {
      const detail = (requestError as { response?: { data?: { detail?: string } } }).response?.data?.detail;
      setError(typeof detail === 'string' ? detail : 'Password update failed. Check your current password and try again.');
    } finally {
      setSaving(false);
    }
  };

  return (
    <main className="relative grid min-h-screen place-items-center bg-slate-950 px-4 py-16 text-white">
      <div className="absolute right-4 top-4 sm:right-6 sm:top-6"><ThemeToggle /></div>
      <section className="w-full max-w-lg rounded-3xl border border-white/10 bg-slate-900/80 p-7 shadow-2xl sm:p-9">
        <div className="mb-6 grid h-12 w-12 place-items-center rounded-2xl bg-amber-400/10 text-amber-200">
          <KeyRound />
        </div>
        <div className="inline-flex items-center gap-2 text-xs font-bold uppercase tracking-widest text-amber-200">
          <ShieldCheck size={15} /> Security step required
        </div>
        <h1 className="mt-3 text-2xl font-black">Change your password</h1>
        <p className="mt-2 text-sm leading-6 text-slate-400">
          {user?.name ? `${user.name}, your administrator account` : 'Your account'} must set a new password before you can access the parking system.
        </p>

        <form onSubmit={submit} className="mt-7 space-y-4">
          <label className="block text-xs font-bold uppercase tracking-wider text-slate-400">
            Current password
            <input required type="password" autoComplete="current-password" value={currentPassword} onChange={event => setCurrentPassword(event.target.value)} className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm text-white outline-none focus:border-indigo-400" />
          </label>
          <label className="block text-xs font-bold uppercase tracking-wider text-slate-400">
            New password
            <input required minLength={12} type="password" autoComplete="new-password" value={newPassword} onChange={event => setNewPassword(event.target.value)} className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm text-white outline-none focus:border-indigo-400" />
          </label>
          <label className="block text-xs font-bold uppercase tracking-wider text-slate-400">
            Confirm new password
            <input required minLength={12} type="password" autoComplete="new-password" value={confirmation} onChange={event => setConfirmation(event.target.value)} className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-950 px-4 py-3 text-sm text-white outline-none focus:border-indigo-400" />
          </label>
          <p className="text-xs leading-5 text-slate-500">Use at least 12 characters with uppercase, lowercase, a number, and a symbol. Recent passwords cannot be reused.</p>
          {error && <p role="alert" className="rounded-xl border border-rose-400/20 bg-rose-400/10 p-3 text-sm text-rose-200">{error}</p>}
          <button type="submit" disabled={saving} className="w-full rounded-xl bg-indigo-500 px-4 py-3 font-bold text-white disabled:opacity-50">{saving ? 'Updating password…' : 'Update password'}</button>
        </form>

        <button type="button" onClick={logout} className="mt-5 inline-flex w-full items-center justify-center gap-2 rounded-xl border border-slate-700 px-4 py-3 text-sm font-bold text-slate-300 hover:bg-slate-800">
          <LogOut size={16} /> Sign out
        </button>
      </section>
    </main>
  );
}
