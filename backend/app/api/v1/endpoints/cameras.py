from pathlib import Path
from uuid import uuid4

import cv2
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from jose import JWTError
from sqlalchemy.orm import Session

from app.api.deps import current_user, require_roles
from app.cameras.stream import CameraStream
from app.core.config import settings
from app.core.database import get_db
from app.core.security import decode_token
from app.models.all_models import Camera, CameraRole, CameraStatus, CameraType, User
from app.services.activity import record_activity

router = APIRouter()
CAMERA_VIDEO_DIR = Path(__file__).resolve().parents[4] / "uploads" / "camera_demos"
MAX_VIDEO_BYTES = 100 * 1024 * 1024
ALLOWED_VIDEO_TYPES = {".mp4", ".avi", ".mov", ".mkv", ".webm"}


def serialize(camera: Camera) -> dict:
    return {
        "camera_id": camera.camera_id,
        "camera_name": camera.camera_name,
        "location": camera.location,
        "camera_role": camera.camera_role.value,
        "camera_type": camera.camera_type.value,
        "stream_url": camera.stream_url,
        "status": camera.status.value,
        "created_at": camera.created_at.isoformat() if camera.created_at else None,
        "updated_at": camera.updated_at.isoformat() if camera.updated_at else None,
    }


@router.get("/")
def list_cameras(db: Session = Depends(get_db), _=Depends(current_user)):
    rows = db.query(Camera).order_by(Camera.camera_role, Camera.camera_id).all()
    return [serialize(camera) for camera in rows]


@router.post("/", status_code=status.HTTP_201_CREATED)
def create_camera(
    payload: dict,
    db: Session = Depends(get_db),
    _=Depends(require_roles("SUPER_ADMIN", "ADMIN")),
):
    name = str(payload.get("camera_name", "")).strip()
    location = str(payload.get("location", "")).strip()
    role = str(payload.get("camera_role", "PARKING_ZONE")).upper()
    camera_type = str(payload.get("camera_type", "DEMO")).upper()
    status_value = str(payload.get("status", "UNKNOWN")).upper()

    if not name or not location:
        raise HTTPException(400, "camera_name and location are required")

    try:
        role_enum = CameraRole(role)
        type_enum = CameraType(camera_type)
        status_enum = CameraStatus(status_value)
    except ValueError as exc:
        raise HTTPException(400, "Invalid camera_role, camera_type, or status") from exc

    if db.query(Camera).filter(Camera.camera_name == name).first():
        raise HTTPException(409, "Camera name already exists")

    if role_enum in (CameraRole.ENTRY, CameraRole.EXIT):
        if db.query(Camera).filter(Camera.camera_role == role_enum).first():
            raise HTTPException(409, f"{role_enum.value} camera already exists")

    camera = Camera(
        camera_name=name,
        location=location,
        camera_role=role_enum,
        camera_type=type_enum,
        stream_url=payload.get("stream_url") or None,
        status=status_enum,
    )
    db.add(camera)
    db.flush()
    record_activity(db, _.user_id, "CAMERA_CREATED", "CAMERA", camera.camera_id, {"camera_name":camera.camera_name,"camera_role":camera.camera_role.value,"camera_type":camera.camera_type.value})
    db.commit()
    db.refresh(camera)
    return serialize(camera)


@router.put("/{camera_id}")
def update_camera(
    camera_id: int,
    payload: dict,
    db: Session = Depends(get_db),
    _=Depends(require_roles("SUPER_ADMIN", "ADMIN")),
):
    camera = db.get(Camera, camera_id)
    if not camera:
        raise HTTPException(404, "Camera not found")

    before={"camera_name":camera.camera_name,"location":camera.location,"camera_role":camera.camera_role.value,"camera_type":camera.camera_type.value,"status":camera.status.value,"stream_url":camera.stream_url}
    if "camera_name" in payload:
        name = str(payload["camera_name"]).strip()
        if not name:
            raise HTTPException(400, "camera_name cannot be empty")
        duplicate = db.query(Camera).filter(
            Camera.camera_name == name,
            Camera.camera_id != camera_id,
        ).first()
        if duplicate:
            raise HTTPException(409, "Camera name already exists")
        camera.camera_name = name

    if "location" in payload:
        camera.location = str(payload["location"]).strip()

    if "camera_role" in payload:
        try:
            new_role = CameraRole(str(payload["camera_role"]).upper())
        except ValueError as exc:
            raise HTTPException(400, "Invalid camera_role") from exc
        if new_role in (CameraRole.ENTRY, CameraRole.EXIT):
            duplicate_role = db.query(Camera).filter(
                Camera.camera_role == new_role,
                Camera.camera_id != camera_id,
            ).first()
            if duplicate_role:
                raise HTTPException(409, f"{new_role.value} camera already exists")
        camera.camera_role = new_role

    if "camera_type" in payload:
        try:
            camera.camera_type = CameraType(str(payload["camera_type"]).upper())
        except ValueError as exc:
            raise HTTPException(400, "Invalid camera_type") from exc

    if "status" in payload:
        try:
            camera.status = CameraStatus(str(payload["status"]).upper())
        except ValueError as exc:
            raise HTTPException(400, "Invalid status") from exc

    if "stream_url" in payload:
        camera.stream_url = payload["stream_url"] or None

    record_activity(db, _.user_id, "CAMERA_UPDATED", "CAMERA", camera.camera_id, {"before":before,"after":{"camera_name":camera.camera_name,"location":camera.location,"camera_role":camera.camera_role.value,"camera_type":camera.camera_type.value,"status":camera.status.value,"stream_url":camera.stream_url}})
    db.commit()
    db.refresh(camera)
    return serialize(camera)


@router.delete("/{camera_id}")
def delete_camera(
    camera_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_roles("SUPER_ADMIN", "ADMIN")),
):
    camera = db.get(Camera, camera_id)
    if not camera:
        raise HTTPException(404, "Camera not found")
    details={"camera_name":camera.camera_name,"camera_role":camera.camera_role.value,"location":camera.location}; camera_id=camera.camera_id
    db.delete(camera)
    record_activity(db, _.user_id, "CAMERA_DELETED", "CAMERA", camera_id, details)
    db.commit()
    return {"message": "Camera deleted successfully"}


@router.post("/{camera_id}/upload-video")
async def upload_demo_video(
    camera_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    user=Depends(require_roles("SUPER_ADMIN", "ADMIN")),
):
    camera = db.get(Camera, camera_id)
    if not camera:
        raise HTTPException(404, "Camera not found")
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in ALLOWED_VIDEO_TYPES:
        raise HTTPException(400, "Upload an MP4, AVI, MOV, MKV, or WebM video")
    if file.content_type and not (
        file.content_type.startswith("video/")
        or file.content_type == "application/octet-stream"
    ):
        raise HTTPException(400, "The uploaded file must be a video")

    CAMERA_VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    target = CAMERA_VIDEO_DIR / f"{uuid4().hex}{suffix}"
    size = 0
    saved = False
    try:
        with target.open("wb") as destination:
            while chunk := await file.read(1024 * 1024):
                size += len(chunk)
                if size > MAX_VIDEO_BYTES:
                    raise HTTPException(413, "Video exceeds the 100 MB upload limit")
                destination.write(chunk)
        if size == 0:
            raise HTTPException(400, "The uploaded video is empty")

        capture = cv2.VideoCapture(str(target))
        try:
            is_readable, _ = capture.read()
        finally:
            capture.release()
        if not is_readable:
            raise HTTPException(422, "OpenCV could not read a frame from this video")

        before = {
            "camera_type": camera.camera_type.value,
            "status": camera.status.value,
            "stream_url": camera.stream_url,
        }
        camera.camera_type = CameraType.UPLOAD
        camera.status = CameraStatus.ONLINE
        camera.stream_url = str(target.resolve())
        record_activity(
            db,
            user.user_id,
            "CAMERA_DEMO_VIDEO_UPLOADED",
            "CAMERA",
            camera.camera_id,
            {"camera_name": camera.camera_name, "bytes": size, "before": before},
        )
        db.commit()
        db.refresh(camera)
        saved = True
        return serialize(camera)
    finally:
        if not saved:
            target.unlink(missing_ok=True)
        await file.close()


@router.get("/{camera_id}/stream")
def stream_camera(
    camera_id: int,
    token: str = Query(..., description="Short-lived JWT/access token used by the camera viewer."),
    db: Session = Depends(get_db),
):
    # Browser <img> cannot attach an Authorization header, so the viewer
    # passes the already-issued JWT as a query parameter. The token is only
    # used to authorize access; the actual camera credentials remain server-side.
    try:
        username = decode_token(token)
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired stream token") from exc

    viewer = db.query(User).filter(
        User.username == username,
        User.is_active.is_(True),
    ).first()
    if not viewer:
        raise HTTPException(status_code=401, detail="Invalid stream user")

    camera = db.get(Camera, camera_id)
    if not camera:
        raise HTTPException(404, "Camera not found")

    if camera.status == CameraStatus.OFFLINE:
        raise HTTPException(503, "Camera is offline")

    if not camera.stream_url:
        raise HTTPException(400, "No stream URL configured for this camera")

    return StreamingResponse(
        CameraStream(camera.stream_url).frames(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
            "X-Accel-Buffering": "no",
        },
    )
