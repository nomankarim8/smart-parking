from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import current_user
from app.api.v1.endpoints import parking, reservations, vehicles
from app.core.database import Base, get_db
from app.models.all_models import (
    ActivityLog,
    Blacklist,
    ParkingRecord,
    ParkingSlot,
    Reservation,
    Role,
    SlotStatus,
    User,
    Vehicle,
    VehicleCategory,
)


def build_client():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    def test_db():
        with factory() as db:
            yield db

    with factory() as db:
        role = Role(role_name="ADMIN", description="Blacklist enforcement test")
        db.add(role)
        db.flush()
        user = User(
            username="blacklist-enforcement",
            email="blacklist-enforcement@example.test",
            password_hash="test-only",
            full_name="Blacklist Enforcement",
            role_id=role.role_id,
        )
        category = VehicleCategory(category_name="CAR")
        db.add_all((user, category))
        db.flush()
        slot = ParkingSlot(
            slot_number="A01",
            category_id=category.category_id,
            status=SlotStatus.AVAILABLE,
        )
        db.add(slot)
        db.commit()
        user_id = user.user_id
        category_id = category.category_id

    app = FastAPI()
    app.include_router(parking.router, prefix="/parking")
    app.include_router(reservations.router, prefix="/reservations")
    app.include_router(vehicles.router, prefix="/vehicles")
    app.dependency_overrides[get_db] = test_db
    app.dependency_overrides[current_user] = lambda: SimpleNamespace(
        user_id=user_id,
        username="blacklist-enforcement",
        role=SimpleNamespace(role_name="ADMIN"),
    )
    return engine, factory, TestClient(app), category_id


def add_blacklist(db, plate_number="DHAKA METRO GA 12-3456"):
    entry = Blacklist(
        plate_number=plate_number,
        reason="Test block",
        added_by=1,
        is_active=True,
    )
    db.add(entry)
    db.commit()
    return entry


def vehicle_payload(category_id, plate_number="DHAKA METRO GA 12-3456"):
    return {"plate_number": plate_number, "category_id": category_id}


def test_blacklisted_vehicle_cannot_be_registered():
    engine, factory, client, category_id = build_client()
    with factory() as db:
        add_blacklist(db)

    with client:
        response = client.post(
            "/vehicles/",
            json=vehicle_payload(category_id),
        )

    assert response.status_code == 409
    with factory() as db:
        assert db.query(Vehicle).count() == 0
    engine.dispose()


def test_blacklisted_registered_vehicle_cannot_enter_and_attempt_is_audited():
    engine, factory, client, category_id = build_client()
    with factory() as db:
        vehicle = Vehicle(
            plate_number="DHAKA METRO GA 12-3456",
            normalized_plate="DHAKA METRO GA 12-3456",
            category_id=category_id,
        )
        db.add(vehicle)
        db.flush()
        add_blacklist(db)

    with client:
        response = client.post(
            "/parking/entry",
            json={
                "license_plate": "DHAKA METRO GA 12-3456",
                "category_id": category_id,
            },
        )

    assert response.status_code == 409
    with factory() as db:
        assert db.query(ParkingRecord).count() == 0
        assert db.query(ParkingSlot).one().status == SlotStatus.AVAILABLE
        assert db.query(ActivityLog).filter_by(
            action="BLACKLIST_ENTRY_BLOCKED"
        ).count() == 1
    engine.dispose()


def test_blacklisted_vehicle_cannot_be_reserved():
    engine, factory, client, category_id = build_client()
    with factory() as db:
        add_blacklist(db)

    with client:
        response = client.post(
            "/reservations/",
            json={
                "plate_number": "DHAKA METRO GA 12-3456",
                "category_id": category_id,
                "mobile_number": "01712345678",
            },
        )

    assert response.status_code == 409
    with factory() as db:
        assert db.query(Vehicle).count() == 0
        assert db.query(Reservation).count() == 0
        assert db.query(ParkingSlot).one().status == SlotStatus.AVAILABLE
    engine.dispose()


def test_reservation_checkin_is_denied_if_vehicle_is_blacklisted_after_booking():
    engine, factory, client, category_id = build_client()
    with client:
        reservation = client.post(
            "/reservations/",
            json={
                "plate_number": "DHAKA METRO GA 12-3456",
                "category_id": category_id,
                "mobile_number": "01712345678",
            },
        )
        assert reservation.status_code == 200
        token = reservation.json()["check_in_token"]

        with factory() as db:
            add_blacklist(db)

        response = client.post(
            "/reservations/check-in",
            json={"token": token},
        )

    assert response.status_code == 409
    with factory() as db:
        assert db.query(ParkingRecord).count() == 0
        assert db.query(Reservation).one().status == "CANCELLED"
        assert db.query(ParkingSlot).one().status == SlotStatus.AVAILABLE
        assert db.query(ActivityLog).filter_by(
            action="BLACKLIST_RESERVATION_CHECKIN_BLOCKED"
        ).count() == 1
    engine.dispose()
