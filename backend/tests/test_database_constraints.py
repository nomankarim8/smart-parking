import pytest
from sqlalchemy import create_engine
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import Base
from app.models.all_models import (
    ParkingRecord,
    ParkingSlot,
    ParkingStatus,
    SlotStatus,
    Vehicle,
    VehicleCategory,
)


def test_generated_unique_column_allows_only_one_active_session_per_vehicle():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)

    with Session(engine) as db:
        category = VehicleCategory(category_name="CAR")
        db.add(category)
        db.flush()
        vehicle = Vehicle(normalized_plate="DHAKA METRO GA 12-3456", plate_number="DHAKA METRO GA 12-3456", category_id=category.category_id)
        first_slot = ParkingSlot(slot_number="A01", category_id=category.category_id, status=SlotStatus.OCCUPIED)
        second_slot = ParkingSlot(slot_number="A02", category_id=category.category_id, status=SlotStatus.OCCUPIED)
        db.add_all((vehicle, first_slot, second_slot))
        db.flush()
        db.add(ParkingRecord(vehicle_id=vehicle.vehicle_id, slot_id=first_slot.slot_id, status=ParkingStatus.PARKED))
        db.commit()

        db.add(ParkingRecord(vehicle_id=vehicle.vehicle_id, slot_id=second_slot.slot_id, status=ParkingStatus.PARKED))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()

        active_count = db.query(ParkingRecord).filter_by(
            vehicle_id=vehicle.vehicle_id,
            status=ParkingStatus.PARKED,
        ).count()
        assert active_count == 1

        db.query(ParkingRecord).filter_by(vehicle_id=vehicle.vehicle_id).update(
            {ParkingRecord.status: ParkingStatus.COMPLETED}
        )
        db.add(ParkingRecord(vehicle_id=vehicle.vehicle_id, slot_id=second_slot.slot_id, status=ParkingStatus.PARKED))
        db.commit()
        assert db.query(ParkingRecord).filter_by(
            vehicle_id=vehicle.vehicle_id,
            status=ParkingStatus.PARKED,
        ).count() == 1

    engine.dispose()
