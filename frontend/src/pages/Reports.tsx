import { useCallback, useEffect, useState } from 'react';
import { Download, FileBarChart2, Search } from 'lucide-react';
import api from '../services/api';

type Summary = {
  start_date: string;
  end_date: string;
  entered: number;
  exited: number;
  revenue: number;
  categories: { category: string; count: number }[];
};

type HistoryItem = {
  record_id: number;
  plate: string;
  category: string;
  slot: string;
  entry_time: string;
  exit_time: string | null;
  status: string;
  payment_status: string | null;
};

type Filters = {
  start_date: string;
  end_date: string;
  plate: string;
};

const todayParts = new Intl.DateTimeFormat('en-CA', {
  timeZone: 'Asia/Dhaka',
  year: 'numeric',
  month: '2-digit',
  day: '2-digit',
}).formatToParts(new Date());
const today = `${todayParts.find(part => part.type === 'year')?.value}-${todayParts.find(part => part.type === 'month')?.value}-${todayParts.find(part => part.type === 'day')?.value}`;
const initialFilters = { start_date: today, end_date: today, plate: '' };
const emptySummary: Summary = {
  start_date: today,
  end_date: today,
  entered: 0,
  exited: 0,
  revenue: 0,
  categories: [],
};

export default function Reports() {
  const [filters, setFilters] = useState<Filters>(initialFilters);
  const [appliedFilters, setAppliedFilters] = useState<Filters>(initialFilters);
  const [summary, setSummary] = useState<Summary>(emptySummary);
  const [items, setItems] = useState<HistoryItem[]>([]);
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState('');
  const pageSize = 25;

  const load = useCallback(async (requestedPage: number) => {
    setLoading(true);
    setError('');
    const params = {
      start_date: appliedFilters.start_date || undefined,
      end_date: appliedFilters.end_date || undefined,
      plate: appliedFilters.plate.trim() || undefined,
    };
    try {
      const [summaryResponse, historyResponse] = await Promise.all([
        api.get<Summary>('/reports/summary', { params }),
        api.get('/reports/history', { params: { ...params, page: requestedPage, page_size: pageSize } }),
      ]);
      setSummary(summaryResponse.data);
      setItems(historyResponse.data.items as HistoryItem[]);
      setTotal(historyResponse.data.total as number);
      setPage(requestedPage);
    } catch {
      setError('Unable to load reports. Check your access and try again.');
    } finally {
      setLoading(false);
    }
  }, [appliedFilters]);

  useEffect(() => {
    void load(1);
  }, [load]);

  const updateFilter = (key: keyof Filters, value: string) => {
    setFilters(current => ({ ...current, [key]: value }));
  };

  const exportCsv = async () => {
    setExporting(true);
    setError('');
    try {
      const response = await api.get('/reports/history.csv', {
        params: {
          start_date: appliedFilters.start_date || undefined,
          end_date: appliedFilters.end_date || undefined,
          plate: appliedFilters.plate.trim() || undefined,
        },
        responseType: 'blob',
      });
      const url = URL.createObjectURL(response.data);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = 'parking_history.csv';
      anchor.click();
      URL.revokeObjectURL(url);
    } catch {
      setError('CSV export failed. Check your access and try again.');
    } finally {
      setExporting(false);
    }
  };

  const maxPage = Math.max(1, Math.ceil(total / pageSize));

  return (
    <div className="p-4 sm:p-6 lg:p-8">
      <header className="mb-7 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <div className="text-xs font-bold uppercase tracking-[.2em] text-indigo-300">Analytics</div>
          <h1 className="mt-1 flex items-center gap-3 text-3xl font-black text-white">
            <FileBarChart2 className="text-indigo-300" /> Reports
          </h1>
          <p className="mt-2 text-sm text-slate-400">Parking activity and revenue for the selected Dhaka-local date range.</p>
        </div>
        <button
          type="button"
          onClick={() => void exportCsv()}
          disabled={exporting || loading}
          className="inline-flex items-center justify-center gap-2 rounded-xl border border-indigo-400/20 bg-indigo-400/10 px-4 py-3 text-sm font-bold text-indigo-100 disabled:opacity-50"
        >
          <Download size={17} /> {exporting ? 'Preparing…' : 'Export filtered CSV'}
        </button>
      </header>

      <section className="glass mb-6 grid gap-4 rounded-2xl p-5 md:grid-cols-[1fr_1fr_1.4fr_auto] md:items-end">
        <label className="text-xs font-bold uppercase tracking-wider text-slate-500">
          Start date
          <input type="date" value={filters.start_date} onChange={event => updateFilter('start_date', event.target.value)} className="mt-2 block w-full rounded-xl border border-white/10 bg-slate-950/70 px-3 py-3 text-sm text-white" />
        </label>
        <label className="text-xs font-bold uppercase tracking-wider text-slate-500">
          End date
          <input type="date" value={filters.end_date} onChange={event => updateFilter('end_date', event.target.value)} className="mt-2 block w-full rounded-xl border border-white/10 bg-slate-950/70 px-3 py-3 text-sm text-white" />
        </label>
        <label className="text-xs font-bold uppercase tracking-wider text-slate-500">
          Plate contains
          <input value={filters.plate} onChange={event => updateFilter('plate', event.target.value)} placeholder="Search normalized plate" className="mt-2 block w-full rounded-xl border border-white/10 bg-slate-950/70 px-3 py-3 text-sm text-white" />
        </label>
        <button type="button" onClick={() => setAppliedFilters(filters)} className="inline-flex items-center justify-center gap-2 rounded-xl bg-indigo-500 px-4 py-3 text-sm font-bold text-white">
          <Search size={16} /> Apply
        </button>
      </section>

      {error && <div role="alert" className="mb-5 rounded-xl border border-rose-400/20 bg-rose-400/10 p-4 text-sm text-rose-200">{error}</div>}

      <section className="mb-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        {[
          ['Date range', `${summary.start_date} — ${summary.end_date}`],
          ['Vehicles entered', summary.entered],
          ['Vehicles exited', summary.exited],
          ['Paid revenue', `৳${summary.revenue.toFixed(2)}`],
        ].map(([label, value]) => (
          <div key={String(label)} className="glass rounded-2xl p-5">
            <div className="text-xs font-bold uppercase tracking-wider text-slate-500">{label}</div>
            <div className="mt-2 text-2xl font-black text-white">{loading ? '…' : value}</div>
          </div>
        ))}
      </section>

      <section className="glass mb-6 rounded-2xl p-5">
        <h2 className="font-bold text-white">Vehicle categories</h2>
        {summary.categories.length === 0
          ? <p className="mt-3 text-sm text-slate-500">{loading ? 'Loading…' : 'No entries in this date range.'}</p>
          : <div className="mt-3 flex flex-wrap gap-2">{summary.categories.map(item => <span key={item.category} className="rounded-full border border-white/10 px-3 py-1.5 text-sm text-slate-300">{item.category}: {item.count}</span>)}</div>}
      </section>

      <section className="glass overflow-hidden rounded-2xl">
        <div className="flex items-center justify-between border-b border-white/5 px-5 py-4">
          <h2 className="font-bold text-white">Parking session history</h2>
          <span className="text-xs text-slate-500">{total.toLocaleString()} records</span>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full min-w-[850px] text-left text-sm">
            <thead className="bg-slate-950/70 text-xs uppercase tracking-widest text-slate-500">
              <tr><th className="px-5 py-4">ID</th><th>Plate</th><th>Category</th><th>Slot</th><th>Entry</th><th>Exit</th><th>Session</th><th>Payment</th></tr>
            </thead>
            <tbody className="divide-y divide-slate-800/70">
              {loading
                ? <tr><td colSpan={8} className="px-5 py-10 text-center text-slate-500">Loading report…</td></tr>
                : items.length === 0
                  ? <tr><td colSpan={8} className="px-5 py-10 text-center text-slate-500">No parking records match these filters.</td></tr>
                  : items.map(item => (
                    <tr key={item.record_id}>
                      <td className="px-5 py-4 text-slate-500">#{item.record_id}</td>
                      <td className="py-4 font-bold text-indigo-300">{item.plate}</td>
                      <td className="py-4 text-slate-400">{item.category}</td>
                      <td className="py-4 text-slate-300">{item.slot}</td>
                      <td className="py-4 text-slate-500">{new Date(item.entry_time).toLocaleString()}</td>
                      <td className="py-4 text-slate-500">{item.exit_time ? new Date(item.exit_time).toLocaleString() : '—'}</td>
                      <td className="py-4 text-slate-300">{item.status}</td>
                      <td className="py-4 text-slate-300">{item.payment_status || '—'}</td>
                    </tr>
                  ))}
            </tbody>
          </table>
        </div>
        <div className="flex items-center justify-between border-t border-white/5 px-5 py-4">
          <span className="text-xs text-slate-500">Page {page} of {maxPage} · CSV is capped at 5,000 rows.</span>
          <div className="flex gap-2">
            <button type="button" disabled={page <= 1 || loading} onClick={() => void load(page - 1)} className="rounded-lg border border-white/10 px-3 py-2 text-xs font-bold text-slate-300 disabled:opacity-40">Previous</button>
            <button type="button" disabled={page >= maxPage || loading} onClick={() => void load(page + 1)} className="rounded-lg border border-white/10 px-3 py-2 text-xs font-bold text-slate-300 disabled:opacity-40">Next</button>
          </div>
        </div>
      </section>
    </div>
  );
}
