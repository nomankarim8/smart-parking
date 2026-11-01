import { ReactNode, useEffect, useRef, useState } from 'react';
import { NavLink, useLocation, useNavigate } from 'react-router-dom';
import {
  Bell,
  CarFront,
  ChevronLeft,
  ChevronRight,
  CircleUserRound,
  ClipboardList,
  CreditCard,
  ChevronDown,
  FileBarChart2,
  History,
  LayoutDashboard,
  LogOut,
  Menu,
  MonitorPlay,
  ParkingSquare,
  Radio,
  ScanLine,
  Settings2,
  ShieldAlert,
  TicketCheck,
  Video,
  X,
} from 'lucide-react';
import type { LucideIcon } from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import ThemeToggle from './ThemeToggle';

type NavItem = {
  to: string;
  label: string;
  Icon: LucideIcon;
  roles?: string[];
};

const OPERATIONS_ROLES = ['SUPER_ADMIN', 'ADMIN', 'OPERATOR'];
const ADMIN_ROLES = ['SUPER_ADMIN', 'ADMIN'];

const nav: NavItem[] = [
  { to: '/', label: 'Dashboard', Icon: LayoutDashboard },
  { to: '/entry', label: 'Vehicle entry', Icon: ScanLine, roles: OPERATIONS_ROLES },
  { to: '/exit', label: 'Vehicle exit', Icon: LogOut, roles: OPERATIONS_ROLES },
  { to: '/vehicles', label: 'Vehicles', Icon: CarFront },
  { to: '/slots', label: 'Parking slots', Icon: ParkingSquare },
  { to: '/reservations', label: 'Reservations', Icon: TicketCheck, roles: OPERATIONS_ROLES },
  { to: '/notifications', label: 'Notifications', Icon: Bell },
  { to: '/payments', label: 'Payments', Icon: CreditCard, roles: OPERATIONS_ROLES },
  { to: '/sensors', label: 'Sensor simulator', Icon: Radio, roles: OPERATIONS_ROLES },
  { to: '/audit', label: 'Audit log', Icon: ClipboardList, roles: ADMIN_ROLES },
  { to: '/history', label: 'Parking history', Icon: History },
  { to: '/blacklist', label: 'Blacklist', Icon: ShieldAlert, roles: ADMIN_ROLES },
  { to: '/cameras', label: 'Camera management', Icon: Video, roles: ADMIN_ROLES },
  { to: '/monitor', label: 'Live monitoring', Icon: MonitorPlay },
  { to: '/reports', label: 'Reports', Icon: FileBarChart2 },
  { to: '/settings', label: 'Settings & pricing', Icon: Settings2 },
];

function getInitialSidebarState() {
  try {
    return localStorage.getItem('smart_parking_sidebar_collapsed') === 'true';
  } catch {
    return false;
  }
}

export default function Layout({ children }: { children: ReactNode }) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const menuButtonRef = useRef<HTMLButtonElement>(null);
  const drawerRef = useRef<HTMLElement>(null);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(getInitialSidebarState);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const allowedNav = nav.filter(item => !item.roles || item.roles.includes(user?.role ?? ''));
  const currentPage = allowedNav.find(item =>
    item.to === '/' ? location.pathname === '/' : location.pathname.startsWith(item.to),
  )?.label ?? 'Smart Parking';
  const sidebarWidth = sidebarCollapsed ? 'lg:ml-20' : 'lg:ml-64';

  useEffect(() => setMobileMenuOpen(false), [location.pathname]);

  useEffect(() => {
    if (!mobileMenuOpen) return;
    const focusable = () => drawerRef.current?.querySelectorAll<HTMLElement>(
      'a[href], button:not(:disabled)',
    );
    focusable()?.[0]?.focus();
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setMobileMenuOpen(false);
        menuButtonRef.current?.focus();
        return;
      }
      if (event.key !== 'Tab') return;
      const items = focusable();
      if (!items?.length) return;
      if (event.shiftKey && document.activeElement === items[0]) {
        event.preventDefault();
        items[items.length - 1].focus();
      } else if (!event.shiftKey && document.activeElement === items[items.length - 1]) {
        event.preventDefault();
        items[0].focus();
      }
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [mobileMenuOpen]);

  const toggleSidebar = () => {
    setSidebarCollapsed(value => {
      const next = !value;
      try {
        localStorage.setItem('smart_parking_sidebar_collapsed', String(next));
      } catch {
        // The sidebar still collapses for this session if storage is unavailable.
      }
      return next;
    });
  };

  const signOut = () => {
    logout();
    navigate('/login', { replace: true });
  };

  const closeMobileMenu = () => {
    setMobileMenuOpen(false);
    window.requestAnimationFrame(() => menuButtonRef.current?.focus());
  };

  const navigation = (compact = false) => (
    <nav aria-label="Main navigation" className="space-y-1">
      {allowedNav.map(({ to, label, Icon }) => (
        <NavLink
          key={to}
          to={to}
          title={compact ? label : undefined}
          end={to === '/'}
          className={({ isActive }) =>
            `app-nav-link flex min-h-11 items-center gap-3 rounded-xl px-3 text-sm font-semibold ${
              compact ? 'justify-center' : ''
            } ${isActive ? 'is-active' : ''}`
          }
        >
          <Icon size={18} aria-hidden="true" />
          {!compact && <span className="truncate">{label}</span>}
        </NavLink>
      ))}
    </nav>
  );

  return (
    <div className={`app-shell min-h-screen ${sidebarWidth}`}>
      <aside
        className={`app-sidebar fixed inset-y-0 left-0 z-30 hidden border-r p-3 transition-[width] duration-200 lg:flex lg:flex-col ${
          sidebarCollapsed ? 'w-20' : 'w-64'
        }`}
      >
        <div className={`mb-7 flex min-h-12 items-center ${sidebarCollapsed ? 'justify-center' : 'gap-3 px-2'}`}>
          <div className="app-brand-mark grid h-10 w-10 shrink-0 place-items-center rounded-xl">
            <ParkingSquare size={21} aria-hidden="true" />
          </div>
          {!sidebarCollapsed && (
            <div className="min-w-0">
              <div className="truncate text-sm font-extrabold tracking-wide">SMART PARKING</div>
              <div className="truncate text-[10px] font-semibold uppercase tracking-wider text-muted">Operations</div>
            </div>
          )}
        </div>

        <div className="min-h-0 flex-1 overflow-y-auto">{navigation(sidebarCollapsed)}</div>

        <div className={`mt-4 border-t pt-4 ${sidebarCollapsed ? 'flex flex-col items-center' : ''}`}>
          {!sidebarCollapsed && (
            <div className="mb-3 flex items-center gap-3 rounded-xl border p-3">
              <CircleUserRound size={20} className="shrink-0 text-muted" aria-hidden="true" />
              <div className="min-w-0">
                <div className="truncate text-sm font-semibold">{user?.name}</div>
                <div className="truncate text-xs text-muted">{user?.role}</div>
              </div>
            </div>
          )}
          <button type="button" onClick={signOut} title="Sign out" className={`app-quiet-button flex min-h-11 items-center gap-3 rounded-xl px-3 text-sm font-semibold ${sidebarCollapsed ? 'justify-center' : 'w-full'}`}>
            <LogOut size={18} aria-hidden="true" />
            {!sidebarCollapsed && 'Sign out'}
          </button>
          <button type="button" onClick={toggleSidebar} aria-label={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'} className="app-quiet-button mt-2 hidden min-h-10 w-full items-center justify-center rounded-xl lg:flex">
            {sidebarCollapsed ? <ChevronRight size={17} /> : <ChevronLeft size={17} />}
          </button>
        </div>
      </aside>

      <header className="app-topbar sticky top-0 z-20 flex min-h-[4.25rem] items-center justify-between gap-3 border-b px-3 sm:px-5 lg:px-7">
        <div className="flex min-w-0 items-center gap-3">
          <button
            type="button"
            ref={menuButtonRef}
            className="app-quiet-button grid h-10 w-10 shrink-0 place-items-center rounded-xl lg:hidden"
            aria-label={mobileMenuOpen ? 'Close navigation menu' : 'Open navigation menu'}
            aria-expanded={mobileMenuOpen}
            aria-controls="mobile-navigation"
            onClick={() => setMobileMenuOpen(value => !value)}
          >
            {mobileMenuOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
          <div className="min-w-0">
            <div className="hidden text-[11px] font-semibold uppercase tracking-[.15em] text-muted sm:block">Operations workspace</div>
            <h1 className="truncate text-base font-bold sm:mt-0.5 sm:text-lg">{currentPage}</h1>
          </div>
        </div>
        <div className="flex shrink-0 items-center gap-2 sm:gap-3">
          <NavLink to="/notifications" aria-label="Notifications" title="Notifications" className="app-quiet-button hidden h-10 w-10 place-items-center rounded-xl sm:grid">
            <Bell size={18} />
          </NavLink>
          <ThemeToggle />
          <details className="account-menu relative hidden border-l pl-3 xl:block">
            <summary className="flex min-h-10 cursor-pointer list-none items-center gap-2 rounded-lg px-2">
              <CircleUserRound size={20} className="shrink-0 text-muted" aria-hidden="true" />
              <span className="min-w-0">
                <span className="block max-w-36 truncate text-sm font-semibold">{user?.name}</span>
                <span className="block text-xs text-muted">{user?.role}</span>
              </span>
              <ChevronDown size={15} className="text-muted" aria-hidden="true" />
            </summary>
            <div className="account-menu-panel absolute right-0 top-full z-50 mt-2 w-52 rounded-xl border p-2 shadow-xl">
              <NavLink to="/settings" className="app-quiet-button block rounded-lg px-3 py-2.5 text-sm font-semibold">Account & settings</NavLink>
              <button type="button" onClick={signOut} className="app-quiet-button flex min-h-10 w-full items-center gap-2 rounded-lg px-3 text-left text-sm font-semibold"><LogOut size={16} />Sign out</button>
            </div>
          </details>
        </div>
      </header>

      {mobileMenuOpen && (
        <div className="fixed inset-0 z-50 lg:hidden">
          <button type="button" aria-label="Close navigation menu" className="absolute inset-0 bg-black/50" onClick={closeMobileMenu} />
          <aside id="mobile-navigation" ref={drawerRef} role="dialog" aria-modal="true" aria-label="Main navigation" className="app-mobile-drawer absolute inset-y-0 left-0 flex w-[min(19rem,88vw)] flex-col border-r p-4 shadow-2xl">
            <div className="mb-5 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="app-brand-mark grid h-10 w-10 place-items-center rounded-xl"><ParkingSquare size={21} /></div>
                <div><div className="text-sm font-extrabold">SMART PARKING</div><div className="text-[10px] uppercase tracking-wider text-muted">Operations</div></div>
              </div>
              <button type="button" aria-label="Close navigation menu" className="app-quiet-button grid h-10 w-10 place-items-center rounded-xl" onClick={closeMobileMenu}><X size={19} /></button>
            </div>
            <div className="min-h-0 flex-1 overflow-y-auto">{navigation()}</div>
            <div className="mt-4 border-t pt-4">
              <div className="mb-3 flex items-center gap-3 rounded-xl border p-3">
                <CircleUserRound size={20} className="text-muted" />
                <div className="min-w-0"><div className="truncate text-sm font-semibold">{user?.name}</div><div className="text-xs text-muted">{user?.role}</div></div>
              </div>
              <button type="button" onClick={signOut} className="app-quiet-button flex min-h-11 w-full items-center gap-3 rounded-xl px-3 text-sm font-semibold"><LogOut size={18} />Sign out</button>
            </div>
          </aside>
        </div>
      )}

      <main className="app-content min-h-[calc(100vh-4.25rem)] min-w-0">{children}</main>
    </div>
  );
}
