from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.core.database import get_db
from app.models.all_models import ActivityLog

router = APIRouter()


@router.get("/")
def activity_history(
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
    _=Depends(require_roles("SUPER_ADMIN", "ADMIN")),
):
    rows = (
        db.query(ActivityLog)
        .order_by(ActivityLog.created_at.desc(), ActivityLog.log_id.desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "log_id": row.log_id,
            "username": row.user.username if row.user else "System",
            "action": row.action,
            "entity_type": row.entity_type,
            "entity_id": row.entity_id,
            "details": row.details or {},
            "created_at": row.created_at.isoformat(),
        }
        for row in rows
    ]
