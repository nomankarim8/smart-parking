/* eslint-disable react-hooks/set-state-in-effect */
import { createContext, ReactNode, useCallback, useContext, useEffect, useLayoutEffect, useMemo, useState } from 'react';
import { useAuth } from './AuthContext';

export type Theme = 'dark' | 'light' | 'system';
type ThemeContextValue = { theme: Theme; setTheme: (theme: Theme) => void };

const GUEST_THEME_KEY = 'smart_parking_theme_guest';
const USER_THEME_PREFIX = 'smart_parking_theme_user:';
const LEGACY_THEME_KEY = 'smart_parking_theme';
const USER_ID_KEY = 'smart_parking_theme_user_id';
const ThemeContext = createContext<ThemeContextValue>({
  theme: 'system',
  setTheme: () => undefined,
});

function isTheme(value: string | null): value is Theme {
  return value === 'dark' || value === 'light' || value === 'system';
}

function getStoredTheme(key: string): Theme | null {
  try {
    const value = localStorage.getItem(key);
    return isTheme(value) ? value : null;
  } catch {
    return null;
  }
}

function initialTheme(): Theme {
  try {
    const token = localStorage.getItem('smart_parking_token');
    const userId = token ? localStorage.getItem(USER_ID_KEY) : null;
    if (userId) {
      const accountTheme = getStoredTheme(`${USER_THEME_PREFIX}${userId}`);
      if (accountTheme) return accountTheme;
    }
    return getStoredTheme(GUEST_THEME_KEY)
      ?? getStoredTheme(LEGACY_THEME_KEY)
      ?? 'system';
  } catch {
    return 'system';
  }
}

function applyTheme(theme: Theme, systemDark: boolean) {
  const resolved = theme === 'system' ? (systemDark ? 'dark' : 'light') : theme;
  document.documentElement.dataset.theme = resolved;
  document.documentElement.dataset.themeMode = theme;
  document.documentElement.style.colorScheme = resolved;
}

export function ThemeProvider({ children }: { children: ReactNode }) {
  const { user, loading } = useAuth();
  const [theme, setThemeState] = useState<Theme>(initialTheme);
  const [systemDark, setSystemDark] = useState(
    () => window.matchMedia?.('(prefers-color-scheme: dark)').matches ?? false,
  );

  useEffect(() => {
    const media = window.matchMedia('(prefers-color-scheme: dark)');
    const update = () => setSystemDark(media.matches);
    update();
    media.addEventListener('change', update);
    return () => media.removeEventListener('change', update);
  }, []);

  useLayoutEffect(() => {
    applyTheme(theme, systemDark);
  }, [theme, systemDark]);

  useLayoutEffect(() => {
    if (loading) return;
    const accountTheme = user
      ? getStoredTheme(`${USER_THEME_PREFIX}${user.id}`)
      : null;
    setThemeState(accountTheme ?? getStoredTheme(GUEST_THEME_KEY) ?? 'system');
  }, [loading, user]);

  const setTheme = useCallback((nextTheme: Theme) => {
    setThemeState(nextTheme);
    if (loading) return;
    const key = user ? `${USER_THEME_PREFIX}${user.id}` : GUEST_THEME_KEY;
    try {
      localStorage.setItem(key, nextTheme);
      if (user) localStorage.setItem(USER_ID_KEY, String(user.id));
      else localStorage.removeItem(USER_ID_KEY);
      localStorage.setItem(LEGACY_THEME_KEY, nextTheme);
    } catch {
      // Theme selection still applies for the current page when storage is unavailable.
    }
  }, [loading, user]);

  const value = useMemo(() => ({ theme, setTheme }), [theme, setTheme]);
  return <ThemeContext.Provider value={value}>{children}</ThemeContext.Provider>;
}

export const useTheme = () => useContext(ThemeContext);
// eslint-disable-next-line react-refresh/only-export-components
