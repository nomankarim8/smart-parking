from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import current_user
from app.api.v1.endpoints import blacklist
from app.core.database import Base, get_db
from app.models.all_models import ActivityLog, Blacklist, Role, User


def make_blacklist_client(role_name="ADMIN"):
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

    with session_factory() as db:
        role = Role(role_id=1, role_name=role_name, description="Test role")
        db.add(role)
        db.add(
            User(
                user_id=1,
                username="blacklist-user",
                email="blacklist-user@example.test",
                password_hash="test-only",
                full_name="Blacklist User",
                role_id=1,
                role=role,
            )
        )
        db.commit()

    app = FastAPI()
    app.include_router(blacklist.router, prefix="/blacklist")
    app.dependency_overrides[get_db] = get_test_db
    app.dependency_overrides[current_user] = lambda: SimpleNamespace(
        user_id=1,
        role=SimpleNamespace(role_name=role_name),
    )
    return engine, session_factory, TestClient(app)


def test_blacklist_deactivation_is_soft_and_audited_and_can_be_reactivated():
    engine, session_factory, client = make_blacklist_client()
    with client:
        created = client.post(
            "/blacklist/",
            json={"plate_number": "DHAKA METRO GA 12-3456", "reason": "Authorized review", "notes": "Case 12"},
        )
        assert created.status_code == 200
        blacklist_id = created.json()["id"]

        deactivated = client.delete(f"/blacklist/{blacklist_id}")
        assert deactivated.status_code == 200
        assert deactivated.json()["is_active"] is False

        with session_factory() as db:
            record = db.get(Blacklist, blacklist_id)
            assert record is not None
            assert record.is_active is False
            assert [row.action for row in db.query(ActivityLog).order_by(ActivityLog.log_id)] == [
                "BLACKLIST_CREATED",
                "BLACKLIST_DEACTIVATED",
            ]

        reactivated = client.post(
            "/blacklist/",
            json={"plate_number": "DHAKA METRO GA 12-3456", "reason": "Recheck", "notes": "Reopened"},
        )
        assert reactivated.status_code == 200
        assert reactivated.json()["id"] == blacklist_id
        assert reactivated.json()["is_active"] is True
        with session_factory() as db:
            assert db.get(Blacklist, blacklist_id).is_active is True
            assert db.query(ActivityLog).order_by(ActivityLog.log_id.desc()).first().action == "BLACKLIST_REACTIVATED"

    engine.dispose()


def test_blacklist_mutations_are_admin_only():
    engine, _session_factory, client = make_blacklist_client("OPERATOR")
    with client:
        response = client.post(
            "/blacklist/",
            json={"plate_number": "DHAKA METRO GA 12-3456", "reason": "Not authorized"},
        )
        assert response.status_code == 403
    engine.dispose()
