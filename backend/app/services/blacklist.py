from sqlalchemy.orm import Session

from app.models.all_models import Blacklist
from app.services.plate import normalize


def active_blacklist_entry(db: Session, plate_number: str) -> Blacklist | None:
    return (
        db.query(Blacklist)
        .filter_by(plate_number=normalize(plate_number), is_active=True)
        .first()
    )
