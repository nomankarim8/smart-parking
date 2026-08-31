from fastapi import APIRouter,Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.all_models import Camera
from app.api.deps import current_user,require_roles
router=APIRouter()
@router.get("/")
def cameras(db:Session=Depends(get_db),_=Depends(current_user)): return [{"camera_id":c.camera_id,"camera_name":c.camera_name,"location":c.location,"camera_type":c.camera_type.value,"status":c.status.value,"stream_url":c.stream_url} for c in db.query(Camera).order_by(Camera.camera_id).all()]
@router.post("/")
def create(payload:dict,db:Session=Depends(get_db),_=Depends(require_roles("SUPER_ADMIN","ADMIN"))):
    c=Camera(camera_name=payload["camera_name"],location=payload["location"],camera_type=payload.get("camera_type","DEMO"),stream_url=payload.get("stream_url"),status="UNKNOWN"); db.add(c); db.commit(); db.refresh(c); return {"camera_id":c.camera_id,"camera_name":c.camera_name}
