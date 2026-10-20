from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import current_user
from app.core.database import get_db
from app.models.all_models import Notification

router = APIRouter()


@router.get("/")
def list_notifications(db: Session = Depends(get_db), _=Depends(current_user)):
    notifications = (
        db.query(Notification)
        .order_by(Notification.created_at.desc(), Notification.notification_id.desc())
        .limit(100)
        .all()
    )
    return [
        {
            "notification_id": item.notification_id,
            "title": item.title,
            "message": item.message,
            "severity": item.severity,
            "is_read": item.is_read,
            "created_at": item.created_at.isoformat(),
        }
        for item in notifications
    ]


@router.post("/{notification_id}/read")
def mark_read(
    notification_id: int,
    db: Session = Depends(get_db),
    _=Depends(current_user),
):
    notification = db.get(Notification, notification_id)
    if not notification:
        raise HTTPException(404, "Notification not found")
    notification.is_read = True
    db.commit()
    return {"notification_id": notification_id, "is_read": True}


@router.post("/read-all")
def mark_all_read(db: Session = Depends(get_db), _=Depends(current_user)):
    db.query(Notification).filter_by(is_read=False).update(
        {Notification.is_read: True},
        synchronize_session=False,
    )
    db.commit()
    return {"ok": True}
