from fastapi import APIRouter,Depends,HTTPException
from pydantic import BaseModel,Field
from sqlalchemy.orm import Session
from app.api.deps import current_user,require_roles
from app.core.database import get_db
from app.models.all_models import PricingRule,VehicleCategory
from app.services.activity import create_notification,record_activity
router=APIRouter()
@router.get("/")
def system_settings(_=Depends(require_roles("SUPER_ADMIN","ADMIN"))): return {"currency":"BDT","timezone":"Asia/Dhaka","alpr_confidence_threshold":0.80,"mode":"LIVE+DEMO"}

class PricingRuleIn(BaseModel):
    hourly_rate:float=Field(ge=0,le=100000)
    min_charge:float=Field(ge=0,le=100000)
    grace_period_minutes:int=Field(ge=0,le=1440)
    daily_max_charge:float|None=Field(default=None,ge=0,le=1000000)
    overnight_charge:float|None=Field(default=None,ge=0,le=1000000)
    is_active:bool=True

@router.get("/pricing")
def pricing_rules(db:Session=Depends(get_db),_=Depends(current_user)):
    rules=db.query(PricingRule).order_by(PricingRule.category_id).all()
    return [{"category_id":r.category_id,"category":db.get(VehicleCategory,r.category_id).category_name,"hourly_rate":float(r.hourly_rate),"min_charge":float(r.min_charge),"grace_period_minutes":r.grace_period_minutes,"daily_max_charge":float(r.daily_max_charge) if r.daily_max_charge is not None else None,"overnight_charge":float(r.overnight_charge) if r.overnight_charge is not None else None,"is_active":r.is_active} for r in rules]

@router.put("/pricing/{category_id}")
def update_pricing_rule(category_id:int,payload:PricingRuleIn,db:Session=Depends(get_db),user=Depends(require_roles("SUPER_ADMIN","ADMIN"))):
    if not db.get(VehicleCategory,category_id):
        raise HTTPException(404,"Vehicle category not found")
    rule=db.query(PricingRule).filter_by(category_id=category_id).with_for_update().first()
    if not rule:
        raise HTTPException(404,"Pricing rule not found")
    old={"hourly_rate":float(rule.hourly_rate),"min_charge":float(rule.min_charge),"grace_period_minutes":rule.grace_period_minutes,"daily_max_charge":float(rule.daily_max_charge) if rule.daily_max_charge is not None else None,"overnight_charge":float(rule.overnight_charge) if rule.overnight_charge is not None else None,"is_active":rule.is_active}
    for key,value in payload.model_dump().items():
        setattr(rule,key,value)
    record_activity(db,user.user_id,"PRICING_RULE_UPDATED","PRICING_RULE",rule.rule_id,{"category_id":category_id,"before":old,"after":payload.model_dump()})
    create_notification(db,"Pricing rule updated",f"Parking fee rules for {db.get(VehicleCategory,category_id).category_name} were updated.","INFO",user.user_id)
    db.commit()
    return {"category_id":category_id,"status":"updated"}
