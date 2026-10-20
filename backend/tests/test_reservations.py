from datetime import datetime, timedelta
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import current_user
from app.api.v1.endpoints.reservations import router
from app.core.database import Base, get_db
from app.models.all_models import (
    ParkingRecord,
    ParkingSlot,
    Reservation,
    SlotStatus,
    Vehicle,
    VehicleCategory,
)
from app.services.reservations import expire_reservations


def test_expired_reservation_releases_its_slot():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    with session_factory() as db:
        category = VehicleCategory(category_id=2, category_name="CAR")
        vehicle = Vehicle(plate_number="TEST 123", normalized_plate="TEST 123", category=category)
        slot = ParkingSlot(slot_number="C01", category=category, status=SlotStatus.RESERVED)
        db.add_all([category, vehicle, slot])
        db.flush()
        db.add(
            Reservation(
                vehicle_id=vehicle.vehicle_id,
                slot_id=slot.slot_id,
                token_hash="0" * 64,
                expires_at=datetime.utcnow() - timedelta(seconds=1),
            )
        )
        db.flush()

        assert expire_reservations(db) == 1
        assert slot.status == SlotStatus.AVAILABLE
        assert db.query(Reservation).one().status == "EXPIRED"

    engine.dispose()


def test_reservation_qr_check_in_is_one_use_and_updates_occupancy():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)

    def get_test_db():
        with session_factory() as db:
            yield db

    staff = SimpleNamespace(
        user_id=1,
        username="test-operator",
        role=SimpleNamespace(role_name="OPERATOR"),
    )
    app = FastAPI()
    app.include_router(router, prefix="/reservations")
    app.dependency_overrides[get_db] = get_test_db
    app.dependency_overrides[current_user] = lambda: staff

    with session_factory() as db:
        category = VehicleCategory(category_id=2, category_name="CAR")
        db.add(category)
        db.add(ParkingSlot(slot_number="C01", category=category, status=SlotStatus.AVAILABLE))
        db.commit()

    with TestClient(app) as client:
        created = client.post(
            "/reservations/",
            json={"plate_number": "TEST 123", "category_id": 2},
        )
        assert created.status_code == 200
        token = created.json()["check_in_token"]
        assert created.json()["expires_at"].endswith("Z")

        with session_factory() as db:
            assert db.query(ParkingSlot).one().status == SlotStatus.RESERVED

        checked_in = client.post("/reservations/check-in", json={"token": token})
        assert checked_in.status_code == 200
        assert checked_in.json()["slot"] == "C01"

        with session_factory() as db:
            assert db.query(ParkingSlot).one().status == SlotStatus.OCCUPIED
            assert db.query(ParkingRecord).count() == 1
            assert db.query(Reservation).one().status == "CHECKED_IN"

        reused = client.post("/reservations/check-in", json={"token": token})
        assert reused.status_code == 409

    engine.dispose()
