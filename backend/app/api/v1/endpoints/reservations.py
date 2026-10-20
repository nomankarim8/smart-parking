from datetime import datetime, timedelta
import hashlib
import secrets

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.deps import current_user, require_roles
from app.core.database import get_db
from app.models.all_models import (
    ParkingRecord,
    ParkingSlot,
    ParkingStatus,
    Reservation,
    SlotStatus,
    Vehicle,
    VehicleCategory,
)
from app.schemas.models import ReservationCheckIn, ReservationIn
from app.services.plate import normalize
from app.services.reservations import expire_reservations
from app.services.activity import create_notification,record_activity

router = APIRouter()
RESERVATION_HOLD_MINUTES = 30


def reservation_data(reservation: Reservation) -> dict:
    return {
        "reservation_id": reservation.reservation_id,
        "plate_number": reservation.vehicle.plate_number,
        "category": reservation.vehicle.category.category_name,
        "slot": reservation.slot.slot_number,
        "status": reservation.status,
        "created_at": f"{reservation.created_at.isoformat()}Z",
        "expires_at": f"{reservation.expires_at.isoformat()}Z",
    }


@router.get("/categories")
def categories(db: Session = Depends(get_db), _=Depends(current_user)):
    return [
        {"category_id": category.category_id, "category_name": category.category_name}
        for category in db.query(VehicleCategory).order_by(VehicleCategory.category_id).all()
    ]


@router.get("/")
def list_reservations(db: Session = Depends(get_db), _=Depends(current_user)):
    expire_reservations(db)
    db.commit()
    reservations = (
        db.query(Reservation)
        .order_by(Reservation.created_at.desc())
        .limit(100)
        .all()
    )
    return [reservation_data(reservation) for reservation in reservations]


@router.post("/")
def create_reservation(
    payload: ReservationIn,
    db: Session = Depends(get_db),
    user=Depends(require_roles("SUPER_ADMIN", "ADMIN", "OPERATOR")),
):
    now = datetime.utcnow()
    expire_reservations(db, now)
    category = db.get(VehicleCategory, payload.category_id)
    if not category:
        raise HTTPException(404, "Vehicle category not found")

    plate = normalize(payload.plate_number)
    vehicle = db.query(Vehicle).filter_by(normalized_plate=plate).first()
    if vehicle and vehicle.category_id != category.category_id:
        raise HTTPException(409, "Vehicle is registered under a different category")
    if vehicle:
        if db.query(ParkingRecord).filter_by(
            vehicle_id=vehicle.vehicle_id, status=ParkingStatus.PARKED
        ).first():
            raise HTTPException(409, "Vehicle already has an active parking session")
        if db.query(Reservation).filter_by(vehicle_id=vehicle.vehicle_id, status="BOOKED").first():
            raise HTTPException(409, "Vehicle already has an active reservation")

    slot = (
        db.query(ParkingSlot)
        .filter(
            ParkingSlot.category_id == category.category_id,
            ParkingSlot.status == SlotStatus.AVAILABLE,
        )
        .order_by(ParkingSlot.slot_number)
        .with_for_update()
        .first()
    )
    if not slot:
        raise HTTPException(409, "No available slot for this vehicle category")

    if not vehicle:
        vehicle = Vehicle(
            plate_number=plate,
            normalized_plate=plate,
            category_id=category.category_id,
        )
        db.add(vehicle)
        db.flush()

    token = secrets.token_urlsafe(32)
    reservation = Reservation(
        vehicle_id=vehicle.vehicle_id,
        slot_id=slot.slot_id,
        token_hash=hashlib.sha256(token.encode("utf-8")).hexdigest(),
        created_by=user.user_id,
        created_at=now,
        expires_at=now + timedelta(minutes=RESERVATION_HOLD_MINUTES),
    )
    slot.status = SlotStatus.RESERVED
    db.add(reservation)
    db.flush()
    create_notification(db,"Reservation confirmed",f"{vehicle.plate_number} reserved slot {slot.slot_number} until {reservation.expires_at.isoformat()}Z.","INFO",user.user_id)
    record_activity(db,user.user_id,"RESERVATION_CREATED","RESERVATION",reservation.reservation_id,{"plate_number":vehicle.plate_number,"slot":slot.slot_number})
    db.commit()
    db.refresh(reservation)
    return {**reservation_data(reservation), "check_in_token": token}


@router.post("/check-in")
def check_in_reservation(
    payload: ReservationCheckIn,
    db: Session = Depends(get_db),
    user=Depends(require_roles("SUPER_ADMIN", "ADMIN", "OPERATOR")),
):
    now = datetime.utcnow()
    expire_reservations(db, now)
    token_hash = hashlib.sha256(payload.token.encode("utf-8")).hexdigest()
    reservation = (
        db.query(Reservation)
        .filter_by(token_hash=token_hash)
        .with_for_update()
        .first()
    )
    if not reservation:
        raise HTTPException(404, "Reservation pass is invalid")
    if reservation.status != "BOOKED":
        raise HTTPException(409, f"Reservation is {reservation.status.lower()}")
    if reservation.expires_at <= now:
        reservation.status = "EXPIRED"
        slot = db.get(ParkingSlot, reservation.slot_id)
        if slot and slot.status == SlotStatus.RESERVED:
            slot.status = SlotStatus.AVAILABLE
        db.commit()
        raise HTTPException(410, "Reservation pass has expired")

    slot = db.query(ParkingSlot).filter_by(slot_id=reservation.slot_id).with_for_update().first()
    if not slot or slot.status != SlotStatus.RESERVED:
        raise HTTPException(409, "Reserved parking slot is no longer available")
    vehicle = reservation.vehicle
    active_record = db.query(ParkingRecord).filter_by(
        vehicle_id=vehicle.vehicle_id, status=ParkingStatus.PARKED
    ).first()
    if active_record:
        raise HTTPException(409, "Vehicle already has an active parking session")

    record = ParkingRecord(
        vehicle_id=vehicle.vehicle_id,
        slot_id=slot.slot_id,
        entry_time=now,
    )
    slot.status = SlotStatus.OCCUPIED
    slot.current_vehicle_id = vehicle.vehicle_id
    reservation.status = "CHECKED_IN"
    db.add(record)
    create_notification(db,"Reserved vehicle checked in",f"{vehicle.plate_number} checked in to slot {slot.slot_number}.","INFO",user.user_id)
    record_activity(db,user.user_id,"RESERVATION_CHECKED_IN","RESERVATION",reservation.reservation_id,{"plate_number":vehicle.plate_number,"slot":slot.slot_number})
    db.commit()
    db.refresh(record)
    return {
        "record_id": record.record_id,
        "license_plate": vehicle.plate_number,
        "slot": slot.slot_number,
        "entry_time": record.entry_time.isoformat(),
        "status": record.status.value,
        "reservation_id": reservation.reservation_id,
        "checked_in_by": user.username,
    }


@router.post("/{reservation_id}/cancel")
def cancel_reservation(
    reservation_id: int,
    db: Session = Depends(get_db),
    _=Depends(require_roles("SUPER_ADMIN", "ADMIN", "OPERATOR")),
):
    expire_reservations(db)
    reservation = (
        db.query(Reservation)
        .filter_by(reservation_id=reservation_id)
        .with_for_update()
        .first()
    )
    if not reservation:
        raise HTTPException(404, "Reservation not found")
    if reservation.status != "BOOKED":
        raise HTTPException(409, f"Reservation is {reservation.status.lower()}")
    reservation.status = "CANCELLED"
    slot = db.get(ParkingSlot, reservation.slot_id)
    if slot and slot.status == SlotStatus.RESERVED:
        slot.status = SlotStatus.AVAILABLE
    record_activity(db,_.user_id,"RESERVATION_CANCELLED","RESERVATION",reservation_id,{"slot":slot.slot_number if slot else None})
    db.commit()
    return {"reservation_id": reservation_id, "status": reservation.status}
