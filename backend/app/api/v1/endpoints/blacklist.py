from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.all_models import Blacklist
from app.services.plate import normalize
from app.api.deps import current_user,require_roles
router=APIRouter()
@router.get("/")
def list_blacklist(db:Session=Depends(get_db),_=Depends(current_user)): return [{"id":b.blacklist_id,"plate_number":b.plate_number,"reason":b.reason,"is_active":b.is_active,"created_at":b.created_at.isoformat()} for b in db.query(Blacklist).order_by(Blacklist.blacklist_id.desc()).all()]
@router.post("/")
def add_blacklist(payload:dict,db:Session=Depends(get_db),user=Depends(require_roles("SUPER_ADMIN","ADMIN"))):
    plate=normalize(payload.get("plate_number",""));
    if not plate or not payload.get("reason"): raise HTTPException(400,"plate_number and reason are required")
    b=Blacklist(plate_number=plate,reason=payload["reason"],added_by=user.user_id,notes=payload.get("notes")); db.add(b); db.commit(); db.refresh(b); return {"id":b.blacklist_id,"plate_number":b.plate_number}
@router.delete("/{blacklist_id}")
def remove(blacklist_id:int,db:Session=Depends(get_db),_=Depends(require_roles("SUPER_ADMIN","ADMIN"))):
    b=db.get(Blacklist,blacklist_id)
    if not b: raise HTTPException(404,"Blacklist entry not found")
    db.delete(b); db.commit(); return {"ok":True}
