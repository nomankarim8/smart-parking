from fastapi import APIRouter,Depends,HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.all_models import Blacklist
from app.services.plate import normalize
from app.api.deps import current_user,require_roles
from app.schemas.models import BlacklistCreate,BlacklistUpdate
from app.services.activity import record_activity
router=APIRouter()

@router.get("/")
def list_blacklist(
    include_inactive:bool=True,
    query:str|None=None,
    db:Session=Depends(get_db),
    _=Depends(current_user),
):
    rows=db.query(Blacklist)
    if not include_inactive:
        rows=rows.filter(Blacklist.is_active.is_(True))
    if query:
        plate=normalize(query)
        rows=rows.filter(Blacklist.plate_number.contains(plate))
    return [
        {"id":b.blacklist_id,"plate_number":b.plate_number,"reason":b.reason,"notes":b.notes,"is_active":b.is_active,"created_at":b.created_at.isoformat(),"added_by":b.added_by}
        for b in rows.order_by(Blacklist.blacklist_id.desc()).limit(500).all()
    ]

@router.post("/")
def add_blacklist(payload:BlacklistCreate,db:Session=Depends(get_db),user=Depends(require_roles("SUPER_ADMIN","ADMIN"))):
    plate=normalize(payload.plate_number)
    reason=payload.reason.strip()
    if not plate or not reason:
        raise HTTPException(422,"A valid normalized plate number and non-empty reason are required")
    b=db.query(Blacklist).filter_by(plate_number=plate).first()
    if b and b.is_active:
        raise HTTPException(409,"This vehicle is already on the blacklist")
    if b:
        before={"is_active":b.is_active,"reason":b.reason,"notes":b.notes}
        b.reason=reason
        b.notes=payload.notes
        b.added_by=user.user_id
        b.is_active=True
        record_activity(db,user.user_id,"BLACKLIST_REACTIVATED","BLACKLIST",b.blacklist_id,{"before":before,"after":{"is_active":True,"reason":b.reason,"notes":b.notes}})
    else:
        b=Blacklist(plate_number=plate,reason=reason,added_by=user.user_id,notes=payload.notes)
        db.add(b)
        db.flush()
        record_activity(db,user.user_id,"BLACKLIST_CREATED","BLACKLIST",b.blacklist_id,{"plate_number":plate,"reason":b.reason,"notes":b.notes,"is_active":True})
    db.commit()
    db.refresh(b)
    return {"id":b.blacklist_id,"plate_number":b.plate_number,"is_active":b.is_active}

@router.put("/{blacklist_id}")
def update_blacklist(blacklist_id:int,payload:BlacklistUpdate,db:Session=Depends(get_db),user=Depends(require_roles("SUPER_ADMIN","ADMIN"))):
    b=db.get(Blacklist,blacklist_id)
    if not b:
        raise HTTPException(404,"Blacklist entry not found")
    changes=payload.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(422,"At least one blacklist field must be provided")
    before={"reason":b.reason,"notes":b.notes}
    if "reason" in changes:
        b.reason=changes["reason"].strip()
        if not b.reason:
            raise HTTPException(422,"Blacklist reason cannot be empty")
    if "notes" in changes:
        b.notes=changes["notes"]
    record_activity(db,user.user_id,"BLACKLIST_UPDATED","BLACKLIST",b.blacklist_id,{"before":before,"after":{"reason":b.reason,"notes":b.notes}})
    db.commit()
    return {"id":b.blacklist_id,"plate_number":b.plate_number,"is_active":b.is_active}

@router.delete("/{blacklist_id}")
def remove(blacklist_id:int,db:Session=Depends(get_db),user=Depends(require_roles("SUPER_ADMIN","ADMIN"))):
    b=db.get(Blacklist,blacklist_id)
    if not b: raise HTTPException(404,"Blacklist entry not found")
    if not b.is_active:
        return {"ok":True,"is_active":False}
    before={"is_active":b.is_active,"reason":b.reason}
    b.is_active=False
    record_activity(db,user.user_id,"BLACKLIST_DEACTIVATED","BLACKLIST",b.blacklist_id,{"before":before,"after":{"is_active":False},"reason":"Authorized staff deactivation"})
    db.commit()
    return {"ok":True,"is_active":False}
