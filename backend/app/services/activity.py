from app.models.all_models import ActivityLog, Notification


def record_activity(
    db,
    user_id: int | None,
    action: str,
    entity_type: str,
    entity_id: int | None,
    details: dict | None = None,
) -> None:
    db.add(
        ActivityLog(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details,
        )
    )


def create_notification(
    db,
    title: str,
    message: str,
    severity: str = "INFO",
    user_id: int | None = None,
) -> None:
    db.add(
        Notification(
            title=title,
            message=message,
            severity=severity,
            created_by=user_id,
        )
    )
