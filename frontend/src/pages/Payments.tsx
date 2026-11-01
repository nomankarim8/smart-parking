import { FormEvent, useCallback, useEffect, useState } from 'react';
import { ReceiptText, RefreshCw, WalletCards } from 'lucide-react';
import api from '../services/api';
import { useAuth } from '../context/AuthContext';

type DuePayment = { record_id: number; plate_number: string; amount_due: number; payment_status: 'PENDING' | 'FAILED' };
type Receipt = { receipt_number: string; record_id: number; plate_number: string; slot: string; duration_minutes: number; gross_amount: number; discount_amount: number; net_amount: number; payment_method: string; payment_status: string; transaction_reference: string | null };
type WalletMethod = 'BKASH_PERSONAL' | 'NAGAD_PERSONAL';
type PaymentConfig = {
  mode: string;
  demo_enabled: boolean;
  providers: Record<'BKASH' | 'NAGAD', { configured: boolean; label: string }>;
  personal_wallets: Record<WalletMethod, { configured: boolean; receiver_number: string | null }>;
};
type WalletSubmission = { submission_id: number; record_id: number; plate_number: string; amount_due: number; submitted_amount: number; method: WalletMethod; transaction_id: string; payer_wallet_masked: string | null; submitted_at: string };

function apiError(error: unknown, fallback: string) {
  if (typeof error === 'object' && error !== null && 'response' in error) {
    const response = error.response;
    if (typeof response === 'object' && response !== null && 'data' in response) {
      const data = response.data;
      if (typeof data === 'object' && data !== null && 'detail' in data && typeof data.detail === 'string') return data.detail;
    }
  }
  return fallback;
}

export default function Payments() {
  const { user } = useAuth();
  const [due, setDue] = useState<DuePayment[]>([]);
  const [receipt, setReceipt] = useState<Receipt | null>(null);
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState<string | null>(null);
  const [paymentConfig, setPaymentConfig] = useState<PaymentConfig | null>(null);
  const [pendingReviews, setPendingReviews] = useState<WalletSubmission[]>([]);
  const [walletForm, setWalletForm] = useState<{ payment: DuePayment; method: WalletMethod } | null>(null);
  const [transactionId, setTransactionId] = useState('');
  const [amount, setAmount] = useState('');
  const [payerWallet, setPayerWallet] = useState('');
  const canVerify = user?.role === 'ADMIN' || user?.role === 'SUPER_ADMIN';

  const load = useCallback(async () => {
    try {
      const response = await api.get<DuePayment[]>('/payments/due');
      setDue(response.data);
      setMessage('');
    } catch (error) {
      setMessage(apiError(error, 'Could not load payments due.'));
    }
  }, []);

  const loadReviews = useCallback(async () => {
    if (!canVerify) return;
    try {
      const response = await api.get<WalletSubmission[]>('/payments/personal-wallet/pending');
      setPendingReviews(response.data);
    } catch (error) {
      setMessage(apiError(error, 'Could not load wallet submissions for review.'));
    }
  }, [canVerify]);

  useEffect(() => {
    api.get<PaymentConfig>('/payments/config')
      .then(response => setPaymentConfig(response.data))
      .catch(error => setMessage(apiError(error, 'Could not load payment configuration.')));
    void load();
    void loadReviews();
    const timer = window.setInterval(() => {
      void load();
      void loadReviews();
    }, 10000);
    return () => window.clearInterval(timer);
  }, [load, loadReviews]);

  const startCheckout = async (recordId: number, provider: 'BKASH' | 'NAGAD') => {
    setBusy(`${recordId}:${provider}`);
    setMessage('');
    try {
      const response = await api.post(`/payments/${recordId}/checkout`, { provider });
      window.location.assign(response.data.checkout_url);
    } catch (error) {
      setMessage(apiError(error, 'Could not start official merchant checkout.'));
    } finally {
      setBusy(null);
    }
  };

  const submitWalletPayment = async (event: FormEvent) => {
    event.preventDefault();
    if (!walletForm) return;
    const busyKey = `${walletForm.payment.record_id}:${walletForm.method}`;
    setBusy(busyKey);
    setMessage('');
    try {
      await api.post(`/payments/personal-wallet/${walletForm.payment.record_id}/submit`, {
        method: walletForm.method,
        transaction_id: transactionId.trim(),
        amount: Number(amount),
        payer_wallet_masked: payerWallet.trim() || null,
      });
      setMessage('Transfer submitted. It remains pending until an administrator checks the receiving wallet history.');
      setWalletForm(null);
      setTransactionId('');
      setPayerWallet('');
      await load();
    } catch (error) {
      setMessage(apiError(error, 'Could not submit the wallet transaction.'));
    } finally {
      setBusy(null);
    }
  };

  const reviewWalletPayment = async (submission: WalletSubmission, decision: 'VERIFIED' | 'REJECTED') => {
    const confirmed = window.confirm(
      decision === 'VERIFIED'
        ? `Confirm that transaction ${submission.transaction_id} and ৳${submission.amount_due.toFixed(2)} were checked against the receiving wallet history?`
        : `Reject wallet transaction ${submission.transaction_id}?`,
    );
    if (!confirmed) return;
    const note = window.prompt('Verification note (recorded in the audit log):', decision === 'VERIFIED' ? 'Matched against receiving wallet history.' : '');
    if (note === null || note.trim().length < 3) {
      setMessage('A verification note of at least 3 characters is required.');
      return;
    }
    setBusy(`review:${submission.submission_id}`);
    setMessage('');
    try {
      const response = await api.post(`/payments/personal-wallet/submissions/${submission.submission_id}/review`, { decision, note: note.trim() });
      if (response.data.receipt) setReceipt(response.data.receipt);
      setMessage(decision === 'VERIFIED' ? 'Wallet transfer verified. The session is now complete.' : 'Wallet transfer rejected. The session remains active and the amount remains due.');
      await Promise.all([load(), loadReviews()]);
    } catch (error) {
      setMessage(apiError(error, 'Could not review this transaction.'));
    } finally {
      setBusy(null);
    }
  };

  return (
    <div className="p-4 sm:p-6 lg:p-8">
      <header className="mb-7 flex flex-wrap items-end justify-between gap-3">
        <div>
          <div className="text-xs font-bold uppercase tracking-[.2em] text-emerald-300">Payments · {paymentConfig?.mode || 'loading'}</div>
          <h1 className="mt-1 text-3xl font-black text-white">Payments & Receipts</h1>
          <p className="mt-1 max-w-3xl text-sm text-slate-400">Personal-wallet transfers are manually reviewed against the receiving wallet. Submitting a transaction ID never marks a payment paid by itself.</p>
        </div>
        <button type="button" onClick={() => { void load(); void loadReviews(); }} className="inline-flex items-center gap-2 rounded-xl border border-slate-700 px-4 py-2.5 text-sm font-bold text-slate-200"><RefreshCw size={15} /> Refresh</button>
      </header>

      {message && <p role="status" className="mb-4 rounded-xl border border-slate-700 bg-slate-900 p-3 text-sm text-slate-300">{message}</p>}

      <div className="grid gap-5 xl:grid-cols-[1fr_.8fr]">
        <section className="glass overflow-hidden rounded-2xl">
          <div className="border-b border-slate-800 p-5"><h2 className="font-bold text-white">Payments due</h2><p className="mt-1 text-xs text-slate-500">{due.length} pending or failed payment(s)</p></div>
          <div className="divide-y divide-slate-800/70">
            {due.map(payment => (
              <article key={payment.record_id} className="flex flex-wrap items-center gap-3 p-4">
                <div className="min-w-36 flex-1"><div className="font-bold text-white">{payment.plate_number}</div><div className="text-xs text-slate-500">Record #{payment.record_id} · {payment.payment_status}</div></div>
                <div className="font-black text-amber-300">৳{payment.amount_due.toFixed(2)}</div>
                <div className="grid w-full grid-cols-2 gap-2 sm:w-auto">
                  {(['BKASH_PERSONAL', 'NAGAD_PERSONAL'] as const).map(method => paymentConfig?.personal_wallets[method].configured && (
                    <button key={method} type="button" onClick={() => { setWalletForm({ payment, method }); setAmount(payment.amount_due.toFixed(2)); setTransactionId(''); setPayerWallet(''); }} className="rounded-lg border border-white/10 bg-slate-800 px-3 py-2 text-xs font-bold text-slate-100 hover:bg-slate-700">
                      Submit {method === 'BKASH_PERSONAL' ? 'bKash' : 'Nagad'} transfer
                    </button>
                  ))}
                  {(['BKASH', 'NAGAD'] as const).map(provider => paymentConfig?.providers[provider].configured && (
                    <button key={provider} type="button" disabled={busy === `${payment.record_id}:${provider}`} onClick={() => void startCheckout(payment.record_id, provider)} className={`rounded-lg px-3 py-2 text-xs font-bold text-white disabled:opacity-40 ${provider === 'BKASH' ? 'bg-pink-600' : 'bg-orange-600'}`}>
                      Official {paymentConfig.providers[provider].label}
                    </button>
                  ))}
                  {paymentConfig?.demo_enabled && <button type="button" onClick={async () => { setBusy(`${payment.record_id}:demo`); try { const response = await api.post(`/payments/${payment.record_id}/demo`, { outcome: 'APPROVED' }); setReceipt(response.data); setMessage('Demo payment approved; do not treat this as a real collection.'); await load(); } catch (error) { setMessage(apiError(error, 'Demo payment failed.')); } finally { setBusy(null); } }} className="rounded-lg bg-emerald-500/10 px-3 py-2 text-xs font-bold text-emerald-300">Demo approve</button>}
                </div>
              </article>
            ))}
            {!due.length && <p className="p-10 text-center text-sm text-slate-500">No payments are currently due.</p>}
          </div>
        </section>

        <section className="glass rounded-2xl p-5">
          <h2 className="mb-4 flex items-center gap-2 font-bold text-white"><ReceiptText size={18} className="text-indigo-300" /> Latest verified receipt</h2>
          {receipt ? <div className="rounded-xl border border-slate-800 bg-slate-950/60 p-4 font-mono text-sm">
            <div className="flex justify-between"><span className="text-slate-500">Receipt</span><span>{receipt.receipt_number}</span></div>
            <div className="mt-2 flex justify-between"><span className="text-slate-500">Plate</span><span>{receipt.plate_number}</span></div>
            <div className="mt-2 flex justify-between"><span className="text-slate-500">Slot</span><span>{receipt.slot}</span></div>
            <div className="mt-2 flex justify-between"><span className="text-slate-500">Duration</span><span>{receipt.duration_minutes} min</span></div>
            <div className="my-3 border-t border-dashed border-slate-700" />
            <div className="flex justify-between font-bold"><span>Total paid</span><span className="text-emerald-300">৳{receipt.net_amount.toFixed(2)}</span></div>
            <div className="mt-3 text-xs text-emerald-300">PAID · {receipt.payment_method}</div>
            {receipt.transaction_reference && <p className="mt-2 break-all text-[10px] text-slate-500">{receipt.transaction_reference}</p>}
            <button type="button" onClick={() => window.print()} className="mt-4 rounded-lg border border-slate-700 px-3 py-2 text-xs font-bold text-slate-200">Print receipt</button>
          </div> : <p className="rounded-xl border border-dashed border-slate-800 p-8 text-center text-sm text-slate-500">A receipt appears after verified payment.</p>}
        </section>
      </div>

      {walletForm && <div className="fixed inset-0 z-50 grid place-items-center overflow-y-auto bg-black/70 p-4">
        <form onSubmit={submitWalletPayment} className="w-full max-w-lg rounded-2xl border border-slate-700 bg-slate-950 p-6 shadow-2xl">
          <h2 className="flex items-center gap-2 text-xl font-black text-white"><WalletCards className="text-cyan-300" /> Submit personal-wallet transfer</h2>
          <p className="mt-2 text-sm text-slate-400">Send using your own official wallet app. This system cannot initiate or automatically verify a personal transfer.</p>
          <div className="mt-4 rounded-xl border border-cyan-300/15 bg-cyan-300/[0.06] p-4 text-sm">
            <div className="text-xs font-bold uppercase tracking-wider text-cyan-200">{walletForm.method === 'BKASH_PERSONAL' ? 'bKash Personal' : 'Nagad Personal'} receiving number</div>
            <div className="mt-1 text-lg font-black text-white">{paymentConfig?.personal_wallets[walletForm.method].receiver_number}</div>
            <div className="mt-2 text-xs text-slate-400">Amount due: ৳{walletForm.payment.amount_due.toFixed(2)} · {walletForm.payment.plate_number} · Record #{walletForm.payment.record_id}</div>
          </div>
          <label className="mt-4 block text-xs font-bold uppercase tracking-wider text-slate-400">Transaction ID
            <input required minLength={4} maxLength={120} value={transactionId} onChange={event => setTransactionId(event.target.value)} className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 text-sm text-white" />
          </label>
          <label className="mt-3 block text-xs font-bold uppercase tracking-wider text-slate-400">Amount sent (BDT)
            <input required type="number" min="0.01" step="0.01" value={amount} onChange={event => setAmount(event.target.value)} className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 text-sm text-white" />
          </label>
          <label className="mt-3 block text-xs font-bold uppercase tracking-wider text-slate-400">Payer wallet (optional, masked only)
            <input maxLength={32} placeholder="01****1234" value={payerWallet} onChange={event => setPayerWallet(event.target.value)} className="mt-2 w-full rounded-xl border border-slate-700 bg-slate-900 px-4 py-3 text-sm text-white" />
          </label>
          <p className="mt-3 text-xs leading-5 text-amber-200">Never enter a wallet PIN, password, or OTP. The payment and parking session stay pending until an administrator checks the actual receiving wallet history.</p>
          <div className="mt-5 flex gap-3">
            <button type="button" onClick={() => setWalletForm(null)} className="flex-1 rounded-xl border border-slate-700 py-3 text-sm font-bold text-slate-300">Cancel</button>
            <button type="submit" disabled={!!busy} className="flex-1 rounded-xl bg-indigo-500 py-3 text-sm font-bold text-white disabled:opacity-50">{busy ? 'Submitting…' : 'Submit for verification'}</button>
          </div>
        </form>
      </div>}

      {canVerify && <section className="glass mt-5 overflow-hidden rounded-2xl">
        <div className="border-b border-slate-800 p-5"><h2 className="font-bold text-white">Personal-wallet verification queue</h2><p className="mt-1 text-xs text-slate-500">Compare each submitted ID and amount to the receiving wallet history before verifying.</p></div>
        {pendingReviews.length ? <div className="divide-y divide-slate-800/70">{pendingReviews.map(submission => <article key={submission.submission_id} className="flex flex-wrap items-center gap-3 p-4">
          <div className="min-w-48 flex-1"><div className="font-bold text-white">{submission.plate_number} · {submission.method.replace('_PERSONAL', '')}</div><div className="mt-1 break-all font-mono text-xs text-cyan-200">{submission.transaction_id}</div><div className="mt-1 text-xs text-slate-500">Record #{submission.record_id} · Submitted {new Date(submission.submitted_at).toLocaleString()}</div></div>
          <div className="text-sm font-bold text-amber-200">Due ৳{submission.amount_due.toFixed(2)} · Sent ৳{submission.submitted_amount.toFixed(2)}</div>
          {submission.payer_wallet_masked && <span className="text-xs text-slate-500">{submission.payer_wallet_masked}</span>}
          <div className="flex gap-2"><button type="button" disabled={!!busy} onClick={() => void reviewWalletPayment(submission, 'VERIFIED')} className="rounded-lg bg-emerald-500/10 px-3 py-2 text-xs font-bold text-emerald-200 disabled:opacity-40">Verify</button><button type="button" disabled={!!busy} onClick={() => void reviewWalletPayment(submission, 'REJECTED')} className="rounded-lg bg-rose-500/10 px-3 py-2 text-xs font-bold text-rose-200 disabled:opacity-40">Reject</button></div>
        </article>)}</div> : <p className="p-8 text-center text-sm text-slate-500">No personal-wallet transactions are waiting for review.</p>}
      </section>}
    </div>
  );
}
