from datetime import datetime

from sqlalchemy.orm import Session

from app.models.all_models import ParkingSlot, Reservation, SlotStatus


def expire_reservations(db: Session, now: datetime | None = None) -> int:
    current_time = now or datetime.utcnow()
    expired = (
        db.query(Reservation)
        .filter(Reservation.status == "BOOKED", Reservation.expires_at <= current_time)
        .with_for_update()
        .all()
    )
    for reservation in expired:
        reservation.status = "EXPIRED"
        slot = db.get(ParkingSlot, reservation.slot_id)
        if slot and slot.status == SlotStatus.RESERVED:
            slot.status = SlotStatus.AVAILABLE
    return len(expired)
