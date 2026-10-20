import { FormEvent, useCallback, useEffect, useState } from 'react';
import { Save, Settings2 } from 'lucide-react';
import api from '../services/api';
import { useAuth } from '../context/AuthContext';

type PricingRule={category_id:number;category:string;hourly_rate:number;min_charge:number;grace_period_minutes:number;daily_max_charge:number|null;overnight_charge:number|null;is_active:boolean};

export default function Settings(){
  const {user}=useAuth();
  const [rules,setRules]=useState<PricingRule[]>([]);
  const [message,setMessage]=useState('');
  const [busy,setBusy]=useState<number|null>(null);
  const canEdit=user?.role==='SUPER_ADMIN'||user?.role==='ADMIN';
  const load=useCallback(async()=>{try{const response=await api.get('/settings/pricing');setRules(response.data);setMessage('')}catch{setMessage('Could not load pricing rules. Please retry.')}},[]);
  useEffect(()=>{void load()},[load]);
  const updateField=(categoryId:number,key:keyof PricingRule,value:number|boolean|null)=>{
    setRules(current=>current.map(rule=>rule.category_id===categoryId?{...rule,[key]:value}:rule));
  };
  const save=async(event:FormEvent,rule:PricingRule)=>{
    event.preventDefault();
    setBusy(rule.category_id);
    setMessage('');
    try{await api.put(`/settings/pricing/${rule.category_id}`,{hourly_rate:Number(rule.hourly_rate),min_charge:Number(rule.min_charge),grace_period_minutes:Number(rule.grace_period_minutes),daily_max_charge:rule.daily_max_charge===null?null:Number(rule.daily_max_charge),overnight_charge:rule.overnight_charge===null?null:Number(rule.overnight_charge),is_active:rule.is_active});setMessage(`${rule.category} pricing updated and recorded in the audit log.`);await load();}
    catch(error:unknown){const response=typeof error==='object'&&error!==null&&'response'in error?error.response:null;const data=typeof response==='object'&&response!==null&&'data'in response?response.data:null;const detail=typeof data==='object'&&data!==null&&'detail'in data?data.detail:null;setMessage(typeof detail==='string'?detail:'Could not save this pricing rule.')}
    finally{setBusy(null)}
  };
  return <div className="p-4 sm:p-6 lg:p-8"><header className="mb-7"><div className="text-xs font-bold uppercase tracking-[.2em] text-indigo-300">System Configuration</div><h1 className="mt-1 flex items-center gap-3 text-3xl font-black text-white"><Settings2 className="text-indigo-300"/> Settings & Pricing</h1><p className="mt-1 text-sm text-slate-500">Manage category fee rules. Admin changes are recorded in the audit log.</p></header>
  {message&&<div role="status" className="mb-4 rounded-xl border border-slate-700 bg-slate-900 p-3 text-sm text-slate-300">{message}</div>}
  {!canEdit&&<div className="mb-4 rounded-xl border border-amber-400/20 bg-amber-400/5 p-3 text-sm text-amber-200">Read-only view. Admin or Super Admin permission is required to edit pricing.</div>}
  <div className="grid gap-4 xl:grid-cols-2">{rules.map(rule=><form key={rule.category_id} onSubmit={event=>void save(event,rule)} className="glass rounded-2xl p-5"><div className="mb-4 flex items-center justify-between"><h2 className="font-bold text-white">{rule.category}</h2><label className="flex items-center gap-2 text-xs text-slate-400"><input type="checkbox" checked={rule.is_active} disabled={!canEdit} onChange={event=>updateField(rule.category_id,'is_active',event.target.checked)}/> Active</label></div><div className="grid gap-3 sm:grid-cols-2">{([['hourly_rate','Hourly rate (৳)'],['min_charge','Minimum charge (৳)'],['grace_period_minutes','Grace period (minutes)'],['daily_max_charge','Daily cap (৳)'],['overnight_charge','Overnight charge (৳)']] as const).map(([key,label])=><label key={key} className="text-xs font-semibold text-slate-500">{label}<input type="number" min="0" step={key==='grace_period_minutes'?'1':'0.01'} value={rule[key]??''} disabled={!canEdit} onChange={event=>updateField(rule.category_id,key,event.target.value===''?null:Number(event.target.value))} className="mt-1.5 w-full rounded-lg border border-slate-800 bg-slate-950 px-3 py-2.5 text-sm text-white disabled:opacity-50"/></label>)}</div><button disabled={!canEdit||busy===rule.category_id} className="mt-4 inline-flex items-center gap-2 rounded-lg bg-indigo-500 px-4 py-2.5 text-xs font-bold text-white disabled:opacity-40"><Save size={14}/>{busy===rule.category_id?'Saving…':'Save rule'}</button></form>)}</div>
  </div>;
}
