import { ReactNode } from 'react';
import { NavLink, useNavigate } from 'react-router-dom';
import { LayoutDashboard, CarFront, ParkingSquare, ScanLine, History, ShieldAlert, Video, FileBarChart2, LogOut, CircleUserRound, Settings2, TicketCheck, Bell, Radio, ClipboardList, CreditCard } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import ThemeToggle from './ThemeToggle';

const nav = [
  ['/', 'Dashboard', LayoutDashboard],
  ['/entry', 'Vehicle Entry', ScanLine],
  ['/exit', 'Vehicle Exit', LogOut],
  ['/vehicles', 'Vehicles', CarFront],
  ['/slots', 'Parking Slots', ParkingSquare],
  ['/reservations', 'Reservations', TicketCheck],
  ['/notifications', 'Notifications', Bell],
  ['/payments', 'Payments', CreditCard],
  ['/sensors', 'Sensor Simulator', Radio],
  ['/audit', 'Admin Audit Log', ClipboardList],
  ['/history', 'History', History],
  ['/blacklist', 'Blacklist', ShieldAlert],
  ['/cameras', 'Cameras', Video],
  ['/reports', 'Reports', FileBarChart2],
  ['/settings', 'Settings', Settings2],
] as const;

export default function Layout({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-slate-950 text-slate-200">
      <aside className="fixed left-0 top-0 bottom-0 hidden w-64 border-r border-slate-800/80 bg-slate-950/95 p-4 lg:flex lg:flex-col">
        <div className="mb-8 flex items-center gap-3 px-2">
          <div className="grid h-11 w-11 place-items-center rounded-2xl bg-indigo-500/15 text-indigo-300"><ParkingSquare /></div>
          <div>
            <div className="text-sm font-black tracking-wide text-white">SMART PARKING</div>
            <div className="text-[11px] text-slate-500">AI-ALPR CONTROL CENTER</div>
          </div>
        </div>
        <nav className="min-h-0 flex-1 space-y-1 overflow-y-auto">
          {nav.map(([to, label, Icon]) => (
            <NavLink key={to} to={to} className={({ isActive }) => `flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-semibold transition ${isActive ? 'bg-indigo-500/15 text-indigo-300' : 'text-slate-400 hover:bg-slate-900 hover:text-white'}`}>
              <Icon size={18} />{label}
            </NavLink>
          ))}
        </nav>
        <div className="mt-auto">
          <div className="mb-3 flex justify-end"><ThemeToggle /></div>
          <div className="mb-3 rounded-2xl border border-slate-800 bg-slate-900/70 p-3">
            <div className="flex items-center gap-3">
              <CircleUserRound className="text-slate-400" />
              <div className="min-w-0">
                <div className="truncate text-sm font-semibold text-white">{user?.name}</div>
                <div className="text-xs text-slate-500">{user?.role}</div>
              </div>
            </div>
          </div>
          <button onClick={() => { logout(); navigate('/login'); }} className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-semibold text-slate-400 hover:bg-rose-500/10 hover:text-rose-300">
            <LogOut size={18} /> Sign out
          </button>
        </div>
      </aside>
      <div className="sticky top-0 z-40 border-b border-slate-800 bg-slate-950/95 backdrop-blur lg:hidden">
        <div className="flex items-center justify-between gap-3 px-4 py-3">
          <div className="flex min-w-0 items-center gap-2">
            <div className="grid h-9 w-9 shrink-0 place-items-center rounded-xl bg-indigo-500/15 text-indigo-300"><ParkingSquare size={19}/></div>
            <div className="min-w-0"><div className="truncate text-xs font-black tracking-wide text-white">SMART PARKING</div><div className="truncate text-[10px] text-slate-500">{user?.name} · {user?.role}</div></div>
          </div>
          <div className="flex shrink-0 items-center gap-2"><ThemeToggle/><button onClick={()=>{logout();navigate('/login')}} aria-label="Sign out" className="rounded-xl border border-slate-700 p-2 text-slate-300"><LogOut size={16}/></button></div>
        </div>
        <nav aria-label="Main navigation" className="flex gap-1 overflow-x-auto px-3 pb-3">
          {nav.map(([to,label,Icon])=><NavLink key={to} to={to} className={({isActive})=>`flex shrink-0 items-center gap-2 rounded-lg px-3 py-2 text-xs font-semibold ${isActive?'bg-indigo-500/15 text-indigo-300':'text-slate-400 hover:bg-slate-900'}`}><Icon size={15}/>{label}</NavLink>)}
        </nav>
      </div>
      <main className="min-h-screen min-w-0 lg:ml-64">{children}</main>
    </div>
  );
}
