import { Suspense, lazy } from 'react';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import Layout from './components/Layout';
import { AuthProvider, useAuth } from './context/AuthContext';
import { ThemeProvider } from './context/ThemeContext';

const Login=lazy(()=>import('./pages/Login'));
const PasswordRotation=lazy(()=>import('./pages/PasswordRotation'));
const Dashboard=lazy(()=>import('./pages/Dashboard'));
const Entry=lazy(()=>import('./pages/Entry'));
const Exit=lazy(()=>import('./pages/Exit'));
const Vehicles=lazy(()=>import('./pages/Vehicles'));
const Slots=lazy(()=>import('./pages/Slots'));
const History=lazy(()=>import('./pages/History'));
const Blacklist=lazy(()=>import('./pages/Blacklist'));
const Reports=lazy(()=>import('./pages/Reports'));
const Cameras=lazy(()=>import('./pages/Cameras'));
const Monitor=lazy(()=>import('./pages/Monitor'));
const Reservations=lazy(()=>import('./pages/Reservations'));
const Notifications=lazy(()=>import('./pages/Notifications'));
const Sensors=lazy(()=>import('./pages/Sensors'));
const Audit=lazy(()=>import('./pages/Audit'));
const Settings=lazy(()=>import('./pages/Settings'));
const Payments=lazy(()=>import('./pages/Payments'));
const PaymentResult=lazy(()=>import('./pages/PaymentResult'));

function Protected(){
  const {user,loading}=useAuth();
  if(loading)return <div className="grid min-h-screen place-items-center text-slate-500">Loading…</div>;
  if(!user)return <Navigate to="/login" replace/>;
  if(user.must_change_password)return <PasswordRotation/>;
  const locationRoles: Record<string,string[]>={
    '/entry':['SUPER_ADMIN','ADMIN','OPERATOR'],
    '/exit':['SUPER_ADMIN','ADMIN','OPERATOR'],
    '/reservations':['SUPER_ADMIN','ADMIN','OPERATOR'],
    '/payments':['SUPER_ADMIN','ADMIN','OPERATOR'],
    '/sensors':['SUPER_ADMIN','ADMIN','OPERATOR'],
    '/audit':['SUPER_ADMIN','ADMIN'],
    '/blacklist':['SUPER_ADMIN','ADMIN'],
    '/cameras':['SUPER_ADMIN','ADMIN'],
  };
  const pathname=window.location.pathname;
  const allowedRoles=locationRoles[pathname];
  if(allowedRoles && !allowedRoles.includes(user.role)){
    return <Layout><div className="grid min-h-[60vh] place-items-center p-6"><div className="max-w-md rounded-2xl border border-rose-400/20 bg-rose-400/5 p-6 text-center"><div className="text-xs font-bold uppercase tracking-wider text-rose-300">403 Forbidden</div><h1 className="mt-2 text-2xl font-black text-white">Access denied</h1><p className="mt-2 text-sm text-slate-400">Your role does not have permission to open this page.</p><Navigate? /></div></div></Layout>;
  }
  return <Layout><Suspense fallback={<div className="grid min-h-[50vh] place-items-center text-slate-500">Loading page…</div>}><Routes>
    <Route path="/" element={<Dashboard/>}/><Route path="/entry" element={<Entry/>}/><Route path="/exit" element={<Exit/>}/><Route path="/vehicles" element={<Vehicles/>}/><Route path="/slots" element={<Slots/>}/><Route path="/reservations" element={<Reservations/>}/><Route path="/notifications" element={<Notifications/>}/><Route path="/sensors" element={<Sensors/>}/><Route path="/payments" element={<Payments/>}/><Route path="/payment-result" element={<PaymentResult/>}/><Route path="/audit" element={<Audit/>}/><Route path="/history" element={<History/>}/><Route path="/blacklist" element={<Blacklist/>}/><Route path="/cameras" element={<Cameras/>}/><Route path="/monitor" element={<Monitor/>}/><Route path="/reports" element={<Reports/>}/><Route path="/settings" element={<Settings/>}/>
  </Routes></Suspense></Layout>;
}

export default function App(){
  return <BrowserRouter><AuthProvider><ThemeProvider><Suspense fallback={<div className="grid min-h-screen place-items-center text-slate-500">Loading…</div>}><Routes><Route path="/login" element={<Login/>}/><Route path="/*" element={<Protected/>}/></Routes></Suspense></ThemeProvider></AuthProvider></BrowserRouter>;
}
