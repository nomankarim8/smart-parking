import os
from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.database import Base, engine as configured_engine
from app.models.all_models import (
    ParkingRecord,
    ParkingSlot,
    ParkingStatus,
    Role,
    SlotStatus,
    User,
    VehicleCategory,
)
from app.api.v1.endpoints.parking import entry
from app.schemas.models import EntryIn


TEST_DATABASE_NAME = os.getenv("MYSQL_TEST_DB_NAME", "")
pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_NAME,
    reason="Set MYSQL_TEST_DB_NAME to a disposable database named smart_parking_test_*.",
)


@pytest.fixture
def mysql_database():
    if not TEST_DATABASE_NAME.startswith("smart_parking_test_"):
        pytest.fail("MYSQL_TEST_DB_NAME must identify a disposable smart_parking_test_* database.")
    test_engine = create_engine(configured_engine.url.set(database=TEST_DATABASE_NAME), pool_pre_ping=True)
    Base.metadata.drop_all(test_engine)
    Base.metadata.create_all(test_engine)
    factory = sessionmaker(bind=test_engine, expire_on_commit=False)

    with Session(test_engine) as db:
        role = Role(role_name="ADMIN", description="MySQL concurrency test")
        category = VehicleCategory(category_name="CAR")
        db.add_all((role, category))
        db.flush()
        user = User(
            username="mysql-test-admin",
            email="mysql-test-admin@example.test",
            password_hash="test-only",
            full_name="MySQL Test",
            role_id=role.role_id,
        )
        db.add(user)
        db.flush()
        db.add_all(
            ParkingSlot(
                slot_number="T{:02d}".format(number),
                category_id=category.category_id,
                status=SlotStatus.AVAILABLE,
            )
            for number in range(1, 3)
        )
        db.commit()
        user_id = user.user_id
        category_id = category.category_id

    yield factory, user_id, category_id
    Base.metadata.drop_all(test_engine)
    test_engine.dispose()


def _attempt_entry(factory, user_id, category_id, plate):
    with factory() as db:
        user = SimpleNamespace(user_id=user_id)
        try:
            result = entry(EntryIn(license_plate=plate, category_id=category_id), db, user)
            return ("created", result["record_id"])
        except HTTPException as exc:
            return ("rejected", exc.status_code)


def test_mysql_concurrent_same_vehicle_creates_at_most_one_active_session(mysql_database):
    factory, user_id, category_id = mysql_database
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(
            lambda _: _attempt_entry(factory, user_id, category_id, "TEST VEHICLE 01"),
            range(2),
        ))

    assert sum(result[0] == "created" for result in results) == 1
    assert sum(result == ("rejected", 409) for result in results) == 1
    with factory() as db:
        assert db.query(ParkingRecord).filter_by(status=ParkingStatus.PARKED).count() == 1
        assert db.query(ParkingSlot).filter_by(status=SlotStatus.OCCUPIED).count() == 1


def test_mysql_concurrent_distinct_vehicles_do_not_overallocate_same_slot(mysql_database):
    factory, user_id, category_id = mysql_database
    with factory() as db:
        second_slot = db.query(ParkingSlot).filter_by(slot_number="T02").one()
        db.delete(second_slot)
        db.commit()

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(
            lambda plate: _attempt_entry(factory, user_id, category_id, plate),
            ("TEST VEHICLE 02", "TEST VEHICLE 03"),
        ))

    assert sum(result[0] == "created" for result in results) == 1
    assert sum(result == ("rejected", 409) for result in results) == 1
    with factory() as db:
        assert db.query(ParkingRecord).filter_by(status=ParkingStatus.PARKED).count() == 1
        assert db.query(ParkingSlot).filter_by(status=SlotStatus.OCCUPIED).count() == 1
