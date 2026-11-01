from pathlib import Path
from uuid import uuid4

import cv2
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import StreamingResponse
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.api.deps import current_user, require_roles
from app.cameras.stream import CameraStream
from app.core.config import settings
from app.core.database import get_db
from app.core.security import create_camera_stream_ticket
from app.schemas.camera import CameraCreate, CameraUpdate
from app.models.all_models import Camera, CameraRole, CameraStatus, CameraType, User
from app.services.activity import record_activity
from app.services.camera_sources import decrypt_camera_source, encrypt_camera_source, validate_camera_source
from app.services.media import camera_demo_root

router = APIRouter()
CAMERA_VIDEO_DIR = camera_demo_root()
MAX_VIDEO_BYTES = 100 * 1024 * 1024
ALLOWED_VIDEO_TYPES = {".mp4", ".avi", ".mov", ".mkv", ".webm"}


def serialize(camera: Camera) -> dict:
    return {
        "camera_id": camera.camera_id,
        "camera_name": camera.camera_name,
        "location": camera.location,
        "camera_role": camera.camera_role.value,
        "camera_type": camera.camera_type.value,
        "stream_configured": bool(camera.stream_url),
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
    payload: CameraCreate,
    db: Session = Depends(get_db),
    _=Depends(require_roles("SUPER_ADMIN", "ADMIN")),
):
    name = payload.camera_name.strip()
    location = payload.location.strip()
    role_enum = CameraRole(payload.camera_role)
    type_enum = CameraType(payload.camera_type)
    try:
        source = encrypt_camera_source(validate_camera_source(type_enum, payload.stream_url))
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc

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
        stream_url=source,
        status=CameraStatus.UNKNOWN,
    )
    db.add(camera)
    db.flush()
    record_activity(db, _.user_id, "CAMERA_CREATED", "CAMERA", camera.camera_id, {"camera_name":camera.camera_name,"camera_role":camera.camera_role.value,"camera_type":camera.camera_type.value,"stream_configured":bool(source)})
    db.commit()
    db.refresh(camera)
    return serialize(camera)


@router.put("/{camera_id}")
def update_camera(
    camera_id: int,
    payload: CameraUpdate,
    db: Session = Depends(get_db),
    _=Depends(require_roles("SUPER_ADMIN", "ADMIN")),
):
    camera = db.get(Camera, camera_id)
    if not camera:
        raise HTTPException(404, "Camera not found")

    fields = payload.dict(exclude_unset=True)
    before={"camera_name":camera.camera_name,"location":camera.location,"camera_role":camera.camera_role.value,"camera_type":camera.camera_type.value,"status":camera.status.value,"stream_configured":bool(camera.stream_url)}
    if "camera_name" in fields:
        name = fields["camera_name"].strip()
        if not name:
            raise HTTPException(400, "camera_name cannot be empty")
        duplicate = db.query(Camera).filter(
            Camera.camera_name == name,
            Camera.camera_id != camera_id,
        ).first()
        if duplicate:
            raise HTTPException(409, "Camera name already exists")
        camera.camera_name = name

    if "location" in fields:
        camera.location = fields["location"].strip()

    if "camera_role" in fields:
        new_role = CameraRole(fields["camera_role"])
        if new_role in (CameraRole.ENTRY, CameraRole.EXIT):
            duplicate_role = db.query(Camera).filter(
                Camera.camera_role == new_role,
                Camera.camera_id != camera_id,
            ).first()
            if duplicate_role:
                raise HTTPException(409, f"{new_role.value} camera already exists")
        camera.camera_role = new_role

    if "camera_type" in fields:
        camera.camera_type = CameraType(fields["camera_type"])

    if "stream_url" in fields or "camera_type" in fields:
        try:
            source = fields.get("stream_url", decrypt_camera_source(camera.stream_url))
            camera.stream_url = encrypt_camera_source(validate_camera_source(camera.camera_type, source))
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from exc

    record_activity(db, _.user_id, "CAMERA_UPDATED", "CAMERA", camera.camera_id, {"before":before,"after":{"camera_name":camera.camera_name,"location":camera.location,"camera_role":camera.camera_role.value,"camera_type":camera.camera_type.value,"status":camera.status.value,"stream_configured":bool(camera.stream_url)}})
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
    details={"camera_name":camera.camera_name,"camera_role":camera.camera_role.value,"location":camera.location,"stream_configured":bool(camera.stream_url)}; camera_id=camera.camera_id
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
            "stream_configured": bool(camera.stream_url),
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
    ticket: str = Query(..., description="Short-lived camera-scoped stream ticket."),
    db: Session = Depends(get_db),
):
    try:
        claims = jwt.decode(
            ticket,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid or expired camera stream ticket") from exc

    if claims.get("scope") != "camera:stream" or claims.get("camera_id") != camera_id:
        raise HTTPException(status_code=401, detail="Camera stream ticket is not valid for this camera")

    viewer = db.query(User).filter(
        User.username == claims.get("sub"),
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
    try:
        source = decrypt_camera_source(camera.stream_url)
        source = validate_camera_source(camera.camera_type, source)
    except ValueError as exc:
        raise HTTPException(503, str(exc)) from exc
    if source and source.lower().startswith(("rtsp://", "rtsps://", "http://", "https://")):
        camera.stream_url = encrypt_camera_source(source)
        db.commit()

    return StreamingResponse(
        CameraStream(source).frames(),
        media_type="multipart/x-mixed-replace; boundary=frame",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Pragma": "no-cache",
            "Expires": "0",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/{camera_id}/stream-ticket")
def create_stream_ticket(
    camera_id: int,
    db: Session = Depends(get_db),
    viewer: User = Depends(current_user),
):
    camera = db.get(Camera, camera_id)
    if not camera:
        raise HTTPException(404, "Camera not found")
    if camera.status == CameraStatus.OFFLINE:
        raise HTTPException(503, "Camera is offline")
    if not camera.stream_url:
        raise HTTPException(400, "No stream URL configured for this camera")
    try:
        validate_camera_source(camera.camera_type, decrypt_camera_source(camera.stream_url))
    except ValueError as exc:
        raise HTTPException(503, str(exc)) from exc
    return {
        "ticket": create_camera_stream_ticket(viewer.username, camera_id),
        "expires_in": 60,
    }
