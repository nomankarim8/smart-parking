/* eslint-disable react-hooks/set-state-in-effect, react-refresh/only-export-components */
import { createContext, ReactNode, useContext, useEffect, useState } from 'react';
import api from '../services/api';
import type { User } from '../types';

interface Ctx {
  user: User | null;
  login: (username: string, password: string) => Promise<void>;
  changePassword: (currentPassword: string, newPassword: string) => Promise<void>;
  logout: () => void;
  loading: boolean;
}

const USER_THEME_ID_KEY = 'smart_parking_theme_user_id';
const AuthContext = createContext<Ctx>({
  user: null,
  login: async () => undefined,
  changePassword: async () => undefined,
  logout: () => undefined,
  loading: true,
});

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const token = localStorage.getItem('smart_parking_token');
    if (!token) {
      setLoading(false);
      return;
    }
    api.get('/auth/me')
      .then(response => setUser(response.data))
      .catch(() => {
        localStorage.removeItem('smart_parking_token');
        localStorage.removeItem(USER_THEME_ID_KEY);
      })
      .finally(() => setLoading(false));
  }, []);

  const login = async (username: string, password: string) => {
    const response = await api.post('/auth/login', { username, password });
    localStorage.setItem('smart_parking_token', response.data.access_token);
    localStorage.setItem(USER_THEME_ID_KEY, String(response.data.user.id));
    setUser(response.data.user);
  };

  const changePassword = async (currentPassword: string, newPassword: string) => {
    const response = await api.post('/auth/change-password', {
      current_password: currentPassword,
      new_password: newPassword,
    });
    localStorage.setItem('smart_parking_token', response.data.access_token);
    setUser(response.data.user);
  };

  const logout = () => {
    localStorage.removeItem('smart_parking_token');
    localStorage.removeItem(USER_THEME_ID_KEY);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, login, changePassword, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
