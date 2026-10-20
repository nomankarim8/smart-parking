import { Suspense, lazy } from 'react';
import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom';
import Layout from './components/Layout';
import { AuthProvider, useAuth } from './context/AuthContext';
import { ThemeProvider } from './context/ThemeContext';

const Login=lazy(()=>import('./pages/Login'));
const Dashboard=lazy(()=>import('./pages/Dashboard'));
const Entry=lazy(()=>import('./pages/Entry'));
const Exit=lazy(()=>import('./pages/Exit'));
const Vehicles=lazy(()=>import('./pages/Vehicles'));
const Slots=lazy(()=>import('./pages/Slots'));
const History=lazy(()=>import('./pages/History'));
const Blacklist=lazy(()=>import('./pages/Blacklist'));
const Simple=lazy(()=>import('./pages/Simple'));
const Cameras=lazy(()=>import('./pages/Cameras'));
const Reservations=lazy(()=>import('./pages/Reservations'));
const Notifications=lazy(()=>import('./pages/Notifications'));
const Sensors=lazy(()=>import('./pages/Sensors'));
const Audit=lazy(()=>import('./pages/Audit'));
const Settings=lazy(()=>import('./pages/Settings'));
const Payments=lazy(()=>import('./pages/Payments'));

function Protected(){
  const {user,loading}=useAuth();
  if(loading)return <div className="grid min-h-screen place-items-center text-slate-500">Loading…</div>;
  if(!user)return <Navigate to="/login" replace/>;
  return <Layout><Suspense fallback={<div className="grid min-h-[50vh] place-items-center text-slate-500">Loading page…</div>}><Routes>
    <Route path="/" element={<Dashboard/>}/><Route path="/entry" element={<Entry/>}/><Route path="/exit" element={<Exit/>}/><Route path="/vehicles" element={<Vehicles/>}/><Route path="/slots" element={<Slots/>}/><Route path="/reservations" element={<Reservations/>}/><Route path="/notifications" element={<Notifications/>}/><Route path="/sensors" element={<Sensors/>}/><Route path="/payments" element={<Payments/>}/><Route path="/audit" element={<Audit/>}/><Route path="/history" element={<History/>}/><Route path="/blacklist" element={<Blacklist/>}/><Route path="/cameras" element={<Cameras/>}/><Route path="/reports" element={<Simple title="Reports & Analytics"/>}/><Route path="/settings" element={<Settings/>}/>
  </Routes></Suspense></Layout>;
}

export default function App(){
  return <ThemeProvider><BrowserRouter><AuthProvider><Suspense fallback={<div className="grid min-h-screen place-items-center text-slate-500">Loading…</div>}><Routes><Route path="/login" element={<Login/>}/><Route path="/*" element={<Protected/>}/></Routes></Suspense></AuthProvider></BrowserRouter></ThemeProvider>;
}
