import axios from 'axios';
const api=axios.create({baseURL:import.meta.env.VITE_API_URL||'http://localhost:8000/api/v1'});
api.interceptors.request.use(c=>{const t=localStorage.getItem('smart_parking_token');if(t)c.headers.Authorization=`Bearer ${t}`;return c});
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error?.response?.status;
    const requestUrl = String(error?.config?.url || '');
    if (status === 401 && !requestUrl.endsWith('/auth/login') && !requestUrl.endsWith('/auth/change-password')) {
      const hadToken = Boolean(localStorage.getItem('smart_parking_token'));
      if (hadToken) {
        localStorage.setItem('smart_parking_session_expired', 'true');
        localStorage.removeItem('smart_parking_token');
        localStorage.removeItem('smart_parking_theme_user_id');
        window.dispatchEvent(new Event('smart-parking-session-expired'));
      }
    }
    return Promise.reject(error);
  },
);
export default api;
