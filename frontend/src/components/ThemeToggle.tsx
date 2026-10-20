import { Moon, Sun } from 'lucide-react';
import { useTheme } from '../context/ThemeContext';

export default function ThemeToggle(){
  const {theme,toggleTheme}=useTheme();
  const next=theme==='dark'?'light':'dark';
  return <button type="button" onClick={toggleTheme} aria-label={`Switch to ${next} mode`} title={`Switch to ${next} mode`} className="inline-flex shrink-0 items-center gap-2 rounded-xl border border-slate-700 px-3 py-2 text-xs font-bold text-slate-300 transition hover:bg-slate-800">
    {theme==='dark'?<Sun size={16}/>:<Moon size={16}/>}<span className="hidden sm:inline">{theme==='dark'?'Light mode':'Dark mode'}</span>
  </button>;
}
