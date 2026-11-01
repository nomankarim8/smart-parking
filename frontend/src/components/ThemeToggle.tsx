import { Monitor, Moon, Sun } from 'lucide-react';
import { Theme, useTheme } from '../context/ThemeContext';

const modes: { value: Theme; label: string; Icon: typeof Sun }[] = [
  { value: 'light', label: 'Light', Icon: Sun },
  { value: 'dark', label: 'Dark', Icon: Moon },
  { value: 'system', label: 'System', Icon: Monitor },
];

export default function ThemeToggle() {
  const { theme, setTheme } = useTheme();
  return (
    <div
      className="theme-selector inline-flex items-center gap-0.5 rounded-xl border p-1"
      role="group"
      aria-label="Color theme"
    >
      {modes.map(({ value, label, Icon }) => (
        <button
          key={value}
          type="button"
          onClick={() => setTheme(value)}
          aria-label={`${label} theme`}
          aria-pressed={theme === value}
          title={`${label} theme`}
          className={`theme-option inline-flex min-h-9 min-w-9 items-center justify-center gap-1.5 rounded-lg px-2 text-xs font-semibold sm:min-h-10 ${
            theme === value ? 'is-selected' : ''
          }`}
        >
          <Icon size={15} aria-hidden="true" />
          <span className="hidden xl:inline">{label}</span>
        </button>
      ))}
    </div>
  );
}
