from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import current_user
from app.api.v1.endpoints import parking, vehicles
from app.core.database import Base, get_db
from app.models.all_models import ParkingRecord, ParkingSlot, ParkingStatus, Role, SlotStatus, User, Vehicle, VehicleCategory


def make_client():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    def get_test_db():
        with factory() as db:
            yield db

    staff = SimpleNamespace(user_id=1, role=SimpleNamespace(role_name="ADMIN"))
    app = FastAPI()
    app.include_router(vehicles.router, prefix="/vehicles")
    app.include_router(parking.router, prefix="/parking")
    app.dependency_overrides[get_db] = get_test_db
    app.dependency_overrides[current_user] = lambda: staff
    return engine, factory, TestClient(app)


def test_vehicle_and_history_pagination_return_metadata_and_boundaries():
    engine, factory, client = make_client()
    with factory() as db:
        role = Role(role_id=1, role_name="ADMIN")
        user = User(user_id=1, username="admin", email="admin@example.local", password_hash="x", full_name="Admin", role_id=1, role=role)
        category = VehicleCategory(category_id=1, category_name="CAR")
        db.add_all([role, user, category])
        db.flush()
        for index in range(3):
            vehicle = Vehicle(plate_number=f"TEST-{index}", normalized_plate=f"TEST-{index}", category_id=1)
            db.add(vehicle)
            db.flush()
            slot = ParkingSlot(slot_number=f"A{index}", category_id=1, status=SlotStatus.AVAILABLE)
            db.add(slot)
            db.flush()
            db.add(ParkingRecord(vehicle_id=vehicle.vehicle_id, slot_id=slot.slot_id, status=ParkingStatus.COMPLETED))
        db.commit()

    first = client.get("/vehicles/?paginated=true&page=1&page_size=2")
    assert first.status_code == 200
    assert first.json()["total"] == 3
    assert len(first.json()["items"]) == 2
    assert first.json()["total_pages"] == 2

    history = client.get("/parking/history?paginated=true&page=2&page_size=2")
    assert history.status_code == 200
    assert history.json()["total"] == 3
    assert len(history.json()["items"]) == 1
    assert history.json()["page"] == 2

    engine.dispose()
