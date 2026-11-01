from datetime import datetime, timedelta
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import current_user
from app.api.v1.endpoints import reports
from app.core.database import Base, get_db
from app.models.all_models import (
    ParkingRecord,
    ParkingSlot,
    ParkingStatus,
    SlotStatus,
    Vehicle,
    VehicleCategory,
)
from app.services.reporting import reporting_window


def make_reports_client():
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

    app = FastAPI()
    app.include_router(reports.router, prefix="/reports")
    app.dependency_overrides[get_db] = get_test_db
    app.dependency_overrides[current_user] = lambda: SimpleNamespace(user_id=1)
    return engine, session_factory, TestClient(app)


def test_report_history_filters_and_paginates_server_side():
    engine, session_factory, client = make_reports_client()
    start, end, utc_start, _utc_end = reporting_window(None, None)
    with session_factory() as db:
        category = VehicleCategory(category_name="CAR")
        db.add(category)
        db.flush()
        vehicle = Vehicle(
            plate_number="DHAKA METRO GA 12-3456",
            normalized_plate="DHAKA METRO GA 12-3456",
            category_id=category.category_id,
        )
        slot = ParkingSlot(
            slot_number="A01",
            category_id=category.category_id,
            status=SlotStatus.AVAILABLE,
        )
        db.add_all((vehicle, slot))
        db.flush()
        for index in range(3):
            db.add(
                ParkingRecord(
                    vehicle_id=vehicle.vehicle_id,
                    slot_id=slot.slot_id,
                    entry_time=utc_start + timedelta(minutes=index + 1),
                    status=ParkingStatus.COMPLETED,
                )
            )
        db.commit()

    with client:
        response = client.get(
            "/reports/history",
            params={
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
                "plate": "METRO GA",
                "page": 2,
                "page_size": 1,
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert data["page"] == 2
        assert len(data["items"]) == 1
        assert data["items"][0]["plate"] == "DHAKA METRO GA 12-3456"

        invalid = client.get("/reports/history", params={"payment_status": "UNKNOWN"})
        assert invalid.status_code == 422

    engine.dispose()
