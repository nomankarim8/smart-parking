from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.all_models import Camera, CameraRole, CameraType, CameraStatus
from app.api.deps import current_user, require_roles

router = APIRouter()

@router.get("/")
def list_cameras(db: Session = Depends(get_db), _=Depends(current_user)):
    rows = db.query(Camera).order_by(Camera.camera_role, Camera.camera_id).all()
    return [{
        "camera_id": c.camera_id,
        "camera_name": c.camera_name,
        "location": c.location,
        "camera_role": c.camera_role.value,
        "camera_type": c.camera_type.value,
        "stream_url": c.stream_url,
        "status": c.status.value,
        "created_at": c.created_at.isoformat() if c.created_at else None,
        "updated_at": c.updated_at.isoformat() if c.updated_at else None,
    } for c in rows]

@router.post("/")
def create_camera(payload: dict, db: Session = Depends(get_db), _=Depends(require_roles("SUPER_ADMIN", "ADMIN"))):
    name = str(payload.get("camera_name", "")).strip()
    location = str(payload.get("location", "")).strip()
    role = str(payload.get("camera_role", "PARKING_ZONE")).upper()
    camera_type = str(payload.get("camera_type", "DEMO")).upper()
    if not name or not location:
        raise HTTPException(400, "camera_name and location are required")
    try:
        role_enum = CameraRole(role)
        type_enum = CameraType(camera_type)
    except ValueError:
        raise HTTPException(400, "Invalid camera_role or camera_type")
    if db.query(Camera).filter(Camera.camera_name == name).first():
        raise HTTPException(409, "Camera name already exists")
    c = Camera(camera_name=name, location=location, camera_role=role_enum, camera_type=type_enum, stream_url=payload.get("stream_url"), status=CameraStatus.UNKNOWN)
    db.add(c); db.commit(); db.refresh(c)
    return {"camera_id": c.camera_id, "message": "Camera added successfully"}

@router.put("/{camera_id}")
def update_camera(camera_id: int, payload: dict, db: Session = Depends(get_db), _=Depends(require_roles("SUPER_ADMIN", "ADMIN"))):
    c = db.get(Camera, camera_id)
    if not c:
        raise HTTPException(404, "Camera not found")
    if "camera_name" in payload:
        c.camera_name = str(payload["camera_name"]).strip()
    if "location" in payload:
        c.location = str(payload["location"]).strip()
    if "stream_url" in payload:
        c.stream_url = payload["stream_url"] or None
    if "camera_role" in payload:
        try: c.camera_role = CameraRole(str(payload["camera_role"]).upper())
        except ValueError: raise HTTPException(400, "Invalid camera_role")
    if "camera_type" in payload:
        try: c.camera_type = CameraType(str(payload["camera_type"]).upper())
        except ValueError: raise HTTPException(400, "Invalid camera_type")
    if "status" in payload:
        try: c.status = CameraStatus(str(payload["status"]).upper())
        except ValueError: raise HTTPException(400, "Invalid status")
    db.commit(); db.refresh(c)
    return {"camera_id": c.camera_id, "message": "Camera updated successfully"}

@router.delete("/{camera_id}")
def delete_camera(camera_id: int, db: Session = Depends(get_db), _=Depends(require_roles("SUPER_ADMIN", "ADMIN"))):
    c = db.get(Camera, camera_id)
    if not c:
        raise HTTPException(404, "Camera not found")
    db.delete(c); db.commit()
    return {"message": "Camera deleted successfully"}
