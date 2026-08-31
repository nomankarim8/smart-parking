import math
from datetime import datetime
from app.models.all_models import PricingRule

def calculate(db, category_id:int, entry:datetime, exit:datetime)->dict:
    rule=db.query(PricingRule).filter(PricingRule.category_id==category_id, PricingRule.is_active==True).first()
    rate=float(rule.hourly_rate if rule else 50); grace=int(rule.grace_period_minutes if rule else 15); minimum=float(rule.min_charge if rule else 50); daily=float(rule.daily_max_charge or 0) if rule else 500
    mins=max(0,int((exit-entry).total_seconds()/60))
    if mins<=grace: amount=0.0
    else:
        billable_hours=math.ceil((mins-grace)/60)
        amount=max(minimum,billable_hours*rate)
        if daily>0: amount=min(amount,daily)
    return {"minutes":mins,"amount":round(amount,2),"rate":rate,"grace":grace}
