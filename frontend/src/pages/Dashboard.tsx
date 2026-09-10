import { useEffect, useState } from 'react';
import api from '../services/api';
import type { Stats, Slot } from '../types';
import SlotGrid from '../components/SlotGrid';
import StatCard from '../components/StatCard';
import CameraSidebar from '../components/CameraSidebar';
import {    
  Activity,
  CarFront,
  CircleDollarSign,
  ParkingCircle,
  ShieldCheck,
} from 'lucide-react';
import {
  Area,
  AreaChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
} from 'recharts';

export default function Dashboard() {
  const [stats, setStats] = useState<Stats | null>(null);
  const [slots, setSlots] = useState<Slot[]>([]);

  const loadDashboard = () =>
    Promise.all([api.get('/dashboard/stats'), api.get('/slots/')]).then(
      ([statsResponse, slotsResponse]) => {
        setStats(statsResponse.data);
        setSlots(slotsResponse.data);
      },
    );

  useEffect(() => {
    loadDashboard();

    const intervalId = setInterval(loadDashboard, 5000);

    return () => clearInterval(intervalId);
  }, []);

  const chartData = (stats?.category_breakdown || []).map((category) => ({
    name: category.category,
    value: category.count,
  }));

  return (
    <div className="flex min-h-screen bg-slate-950">
      <div className="min-w-0 flex-1 p-4 sm:p-6 lg:p-8">
        <header className="mb-7 flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
          <div>
            <div className="text-xs font-bold uppercase tracking-[.2em] text-indigo-300">
              Operations Overview
            </div>
            <h1 className="mt-1 text-3xl font-black text-white">
              Smart Parking Control Center
            </h1>
            <p className="mt-1 text-sm text-slate-500">
              AI-assisted live parking management
            </p>
          </div>

          <div className="flex items-center gap-2 rounded-full border border-emerald-500/20 bg-emerald-500/10 px-4 py-2 text-xs font-bold text-emerald-300">
            <span className="h-2 w-2 rounded-full bg-emerald-400" />
            SYSTEM ONLINE
          </div>
        </header>

        <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-5">
          <StatCard
            label="Total Slots"
            value={stats?.total_slots ?? '—'}
            icon={<ParkingCircle />}
          />
          <StatCard
            label="Available"
            value={stats?.available_slots ?? '—'}
            icon={<CircleDollarSign />}
          />
          <StatCard
            label="Occupied"
            value={stats?.occupied_slots ?? '—'}
            icon={<CarFront />}
          />
          <StatCard
            label="Currently Parked"
            value={stats?.currently_parked ?? '—'}
            icon={<Activity />}
          />
          <StatCard
            label="Today's Revenue"
            value={stats ? `৳${stats.today_revenue.toFixed(0)}` : '—'}
            icon={<ShieldCheck />}
          />
        </div>

        <div className="mt-6 grid gap-5 xl:grid-cols-[1.6fr_.9fr]">
          <SlotGrid slots={slots} />

          <div className="glass rounded-2xl p-5">
            <div className="mb-4">
              <h3 className="font-bold text-white">Vehicle Category Activity</h3>
              <p className="text-xs text-slate-500">
                Today's entry distribution
              </p>
            </div>

            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={chartData}>
                  <XAxis dataKey="name" stroke="#64748b" fontSize={10} />
                  <Tooltip
                    contentStyle={{
                      background: '#0f172a',
                      border: '1px solid #334155',
                      borderRadius: 12,
                    }}
                  />
                  <Area
                    type="monotone"
                    dataKey="value"
                    stroke="#818cf8"
                    fill="#6366f1"
                    fillOpacity={0.18}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>

            <div className="mt-3 rounded-xl border border-slate-800 bg-slate-950/50 p-4">
              <div className="text-xs text-slate-500">Occupancy</div>
              <div className="mt-2 text-2xl font-black text-white">
                {stats?.occupancy ?? 0}%
              </div>
            </div>
          </div>
        </div>

        <CameraSidebar />
      </div>
    </div>
  );
}
