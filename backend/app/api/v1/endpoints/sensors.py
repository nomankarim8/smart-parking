from enum import Enum

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import require_roles
from app.core.database import get_db
from app.models.all_models import (
    ParkingRecord,
    ParkingStatus,
    ParkingSlot,
    SensorEvent,
    SlotStatus,
)
from app.services.activity import record_activity

router = APIRouter()


class SensorState(str, Enum):
    OCCUPIED = "OCCUPIED"
    AVAILABLE = "AVAILABLE"


class SensorSimulationIn(BaseModel):
    slot_id: int
    state: SensorState


@router.post("/simulate")
def simulate_sensor(
    payload: SensorSimulationIn,
    db: Session = Depends(get_db),
    user=Depends(require_roles("SUPER_ADMIN", "ADMIN", "OPERATOR")),
):
    slot = (
        db.query(ParkingSlot)
        .filter_by(slot_id=payload.slot_id)
        .with_for_update()
        .first()
    )
    if not slot:
        raise HTTPException(404, "Parking slot not found")
    if slot.status in (SlotStatus.RESERVED, SlotStatus.MAINTENANCE):
        raise HTTPException(409, f"Cannot simulate a sensor event for a {slot.status.value.lower()} slot")

    active_record = (
        db.query(ParkingRecord)
        .filter_by(slot_id=slot.slot_id, status=ParkingStatus.PARKED)
        .first()
    )
    if active_record and payload.state == SensorState.AVAILABLE:
        raise HTTPException(409, "Cannot clear a slot linked to an active parking session")
    if active_record and payload.state == SensorState.OCCUPIED:
        raise HTTPException(409, "Slot is already occupied by a registered vehicle")

    new_status = SlotStatus(payload.state.value)
    previous_status = slot.status
    if previous_status == new_status:
        raise HTTPException(409, f"Slot is already {new_status.value.lower()}")
    slot.status = new_status
    if new_status == SlotStatus.AVAILABLE:
        slot.current_vehicle_id = None
    db.add(
        SensorEvent(
            slot_id=slot.slot_id,
            previous_status=previous_status.value,
            new_status=new_status.value,
            created_by=user.user_id,
        )
    )
    record_activity(
        db,
        user.user_id,
        "SENSOR_SIMULATED",
        "PARKING_SLOT",
        slot.slot_id,
        {"slot_number": slot.slot_number, "from": previous_status.value, "to": new_status.value},
    )
    db.commit()
    return {
        "slot_id": slot.slot_id,
        "slot_number": slot.slot_number,
        "previous_status": previous_status.value,
        "status": slot.status.value,
        "source": "SIMULATED",
    }


@router.get("/events")
def sensor_events(
    db: Session = Depends(get_db),
    _=Depends(require_roles("SUPER_ADMIN", "ADMIN", "OPERATOR")),
):
    events = db.query(SensorEvent).order_by(SensorEvent.created_at.desc()).limit(100).all()
    return [
        {
            "event_id": event.event_id,
            "slot_id": event.slot_id,
            "slot_number": event.slot.slot_number,
            "previous_status": event.previous_status,
            "new_status": event.new_status,
            "source": event.source,
            "created_at": event.created_at.isoformat(),
        }
        for event in events
    ]
