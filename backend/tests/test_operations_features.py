from datetime import datetime, timedelta
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import pytest

from app.api.deps import current_user
from app.api.v1.endpoints import audit, dashboard, notifications, parking, payments, sensors, settings
from app.core.database import Base, get_db
from app.models.all_models import (
    ParkingRecord,
    ParkingSlot,
    ParkingStatus,
    GatewayPayment,
    Payment,
    PaymentMethod,
    PaymentStatus,
    PricingRule,
    Role,
    SlotStatus,
    User,
    Vehicle,
    VehicleCategory,
)


def make_client():
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
        username="test-admin",
        role=SimpleNamespace(role_name="ADMIN"),
    )
    app = FastAPI()
    app.include_router(audit.router, prefix="/audit")
    app.include_router(dashboard.router, prefix="/dashboard")
    app.include_router(notifications.router, prefix="/notifications")
    app.include_router(parking.router, prefix="/parking")
    app.include_router(payments.router, prefix="/payments")
    app.include_router(sensors.router, prefix="/sensors")
    app.include_router(settings.router, prefix="/settings")
    app.dependency_overrides[get_db] = get_test_db
    app.dependency_overrides[current_user] = lambda: staff
    client = TestClient(app)
    return engine, session_factory, client


def seed_staff(db):
    role = Role(role_id=1, role_name="ADMIN", description="Test admin")
    db.add(role)
    db.add(
        User(
            user_id=1,
            username="test-admin",
            email="test-admin@example.local",
            password_hash="not-used",
            full_name="Test Admin",
            role_id=1,
            is_active=True,
            role=role,
        )
    )
    category = VehicleCategory(category_id=2, category_name="CAR")
    vehicle = Vehicle(
        plate_number="TEST 123",
        normalized_plate="TEST 123",
        category=category,
    )
    slot = ParkingSlot(slot_number="C01", category=category, status=SlotStatus.AVAILABLE)
    pricing = PricingRule(
        category_id=2,
        hourly_rate=50,
        min_charge=50,
        grace_period_minutes=15,
        daily_max_charge=500,
        overnight_charge=100,
        is_active=True,
    )
    db.add_all([category, vehicle, slot, pricing])
    db.flush()
    return vehicle, slot


def create_pending_payment(session_factory):
    with session_factory() as db:
        vehicle, slot = seed_staff(db)
        record = ParkingRecord(
            vehicle_id=vehicle.vehicle_id,
            slot_id=slot.slot_id,
            entry_time=datetime.utcnow() - timedelta(hours=2),
            exit_time=datetime.utcnow(),
            status=ParkingStatus.COMPLETED,
        )
        db.add(record)
        db.flush()
        db.add(
            Payment(
                record_id=record.record_id,
                record=record,
                total_duration_minutes=120,
                gross_amount=100,
                discount_amount=0,
                net_amount=100,
                payment_method=PaymentMethod.CARD,
                payment_status=PaymentStatus.PENDING,
                created_by=1,
            )
        )
        db.commit()
        return record.record_id


def test_demo_payment_updates_status_receipt_notifications_and_audit(monkeypatch):
    engine, session_factory, client = make_client()
    with session_factory() as db:
        vehicle, slot = seed_staff(db)
        record = ParkingRecord(
            vehicle_id=vehicle.vehicle_id,
            slot_id=slot.slot_id,
            entry_time=datetime.utcnow() - timedelta(hours=2),
            exit_time=datetime.utcnow(),
            status=ParkingStatus.COMPLETED,
        )
        db.add(record)
        db.flush()
        db.add(
            Payment(
                record_id=record.record_id,
                record=record,
                total_duration_minutes=120,
                gross_amount=100,
                discount_amount=0,
                net_amount=100,
                payment_method=PaymentMethod.CARD,
                payment_status=PaymentStatus.PENDING,
                created_by=1,
            )
        )
        db.commit()
        record_id = record.record_id

    with client:
        monkeypatch.setattr(payments.settings, "PAYMENT_DEMO_ENABLED", False)
        assert client.post(
            f"/payments/{record_id}/demo",
            json={"outcome": "APPROVED"},
        ).status_code == 403

        monkeypatch.setattr(payments.settings, "PAYMENT_DEMO_ENABLED", True)
        approved = client.post(
            f"/payments/{record_id}/demo",
            json={"outcome": "APPROVED"},
        )
        assert approved.status_code == 200
        assert approved.json()["payment_status"] == "PAID"
        assert approved.json()["receipt_number"].startswith("SP-")
        assert approved.json()["transaction_reference"].startswith("DEMO-")
        assert client.get(f"/payments/{record_id}/receipt").json()["payment_status"] == "PAID"
        assert client.post(
            f"/payments/{record_id}/demo",
            json={"outcome": "APPROVED"},
        ).status_code == 409
        assert client.get("/payments/due").json() == []
        assert client.get("/notifications/").json()[0]["title"] == "Demo payment received"
        assert client.get("/audit/").json()[0]["action"] == "DEMO_PAYMENT_APPROVED"

    engine.dispose()


@pytest.mark.parametrize(
    ("provider", "checkout_url"),
    [
        ("BKASH", "https://checkout.bka.sh/checkout/mock"),
        ("NAGAD", "https://sandbox.mynagad.com/checkout/mock"),
    ],
)
def test_gateway_checkout_starts_for_configured_provider(
    monkeypatch,
    provider,
    checkout_url,
):
    engine, session_factory, client = make_client()
    record_id = create_pending_payment(session_factory)
    monkeypatch.setattr(payments, "gateway_is_configured", lambda _provider: True)
    monkeypatch.setattr(
        payments,
        "start_gateway_payment",
        lambda attempt, amount: {
            "provider_payment_id": f"provider-{provider.lower()}-ref",
            "checkout_url": checkout_url,
        },
    )

    with client:
        response = client.post(
            f"/payments/{record_id}/checkout",
            json={"provider": provider},
        )
        assert response.status_code == 200
        assert response.json()["checkout_url"] == checkout_url
        assert response.json()["provider"] == provider
        assert response.json()["status"] == "INITIATED"
        with session_factory() as db:
            attempt = db.query(GatewayPayment).one()
            assert attempt.provider_payment_id == f"provider-{provider.lower()}-ref"
            assert db.query(Payment).one().payment_status == PaymentStatus.PENDING

    engine.dispose()


@pytest.mark.parametrize(
    ("provider", "callback_path", "currency", "amount", "attempt_status", "payment_status"),
    [
        (
            "BKASH",
            "/payments/bkash/callback?paymentID=mock-bkash-ref&status=success",
            "BDT",
            "100.00",
            "PAID",
            PaymentStatus.PAID,
        ),
        (
            "NAGAD",
            "/payments/nagad/callback?payment_ref_id=mock-nagad-ref",
            "050",
            "99.00",
            "REVIEW",
            PaymentStatus.PENDING,
        ),
    ],
)
def test_gateway_callback_uses_verified_amount_and_currency(
    monkeypatch,
    provider,
    callback_path,
    currency,
    amount,
    attempt_status,
    payment_status,
):
    engine, session_factory, client = make_client()
    record_id = create_pending_payment(session_factory)
    provider_reference = f"mock-{provider.lower()}-ref"
    with session_factory() as db:
        payment = db.query(Payment).one()
        db.add(
            GatewayPayment(
                payment_id=payment.payment_id,
                provider=provider,
                invoice_number=f"invoice-{provider.lower()}",
                provider_payment_id=provider_reference,
                status="INITIATED",
            )
        )
        db.commit()

    monkeypatch.setattr(
        payments,
        "verify_gateway_payment",
        lambda attempt, params: {
            "completed": True,
            "transaction_reference": f"verified-{provider.lower()}-transaction",
            "amount": amount,
            "currency": currency,
        },
    )

    with client:
        response = client.get(callback_path, follow_redirects=False)
        assert response.status_code == 303
        assert f"record_id={record_id}" in response.headers["location"]
        with session_factory() as db:
            assert db.query(Payment).one().payment_status == payment_status
            assert db.query(GatewayPayment).one().status == attempt_status

    engine.dispose()


def test_simulated_sensor_persists_slot_state_and_rejects_reserved_slot():
    engine, session_factory, client = make_client()
    with session_factory() as db:
        _, slot = seed_staff(db)
        db.commit()
        slot_id = slot.slot_id

    with client:
        occupied = client.post(
            "/sensors/simulate",
            json={"slot_id": slot_id, "state": "OCCUPIED"},
        )
        assert occupied.status_code == 200
        assert occupied.json()["source"] == "SIMULATED"
        with session_factory() as db:
            assert db.get(ParkingSlot, slot_id).status == SlotStatus.OCCUPIED
        assert client.get("/sensors/events").json()[0]["new_status"] == "OCCUPIED"

        released = client.post(
            "/sensors/simulate",
            json={"slot_id": slot_id, "state": "AVAILABLE"},
        )
        assert released.status_code == 200
        assert client.get("/audit/").json()[0]["action"] == "SENSOR_SIMULATED"

    engine.dispose()


def test_forecast_returns_hourly_demand_and_validates_range():
    engine, session_factory, client = make_client()
    with session_factory() as db:
        seed_staff(db)
        db.commit()

    with client:
        response = client.get("/dashboard/forecast?hours=3")
        assert response.status_code == 200
        assert response.json()["based_on_days"] == 56
        assert len(response.json()["forecast"]) == 3
        assert response.json()["forecast"][0]["demand"] in {"LOW", "MODERATE", "HIGH"}
        assert client.get("/dashboard/forecast?hours=100").status_code == 400

    engine.dispose()


def test_exit_releases_slot_and_creates_pending_payment_due_notification():
    engine, session_factory, client = make_client()
    with session_factory() as db:
        vehicle, slot = seed_staff(db)
        slot.status = SlotStatus.OCCUPIED
        slot.current_vehicle_id = vehicle.vehicle_id
        record = ParkingRecord(
            vehicle_id=vehicle.vehicle_id,
            slot_id=slot.slot_id,
            entry_time=datetime.utcnow() - timedelta(hours=2),
            status=ParkingStatus.PARKED,
        )
        db.add(record)
        db.commit()

    with client:
        response = client.post(
            "/parking/exit",
            json={"license_plate": "TEST 123", "payment_method": "CASH"},
        )
        assert response.status_code == 200
        assert response.json()["payment_status"] == "PENDING"
        record_id = response.json()["record_id"]
        assert client.get("/payments/due").json()[0]["record_id"] == record_id
        assert client.get("/notifications/").json()[0]["title"] == "Payment due"
        with session_factory() as db:
            assert db.query(ParkingSlot).one().status == SlotStatus.AVAILABLE

    engine.dispose()


def test_pricing_update_is_written_to_admin_audit():
    engine, session_factory, client = make_client()
    with session_factory() as db:
        seed_staff(db)
        db.commit()

    with client:
        response = client.put(
            "/settings/pricing/2",
            json={
                "hourly_rate": 75,
                "min_charge": 60,
                "grace_period_minutes": 10,
                "daily_max_charge": 600,
                "overnight_charge": 120,
                "is_active": True,
            },
        )
        assert response.status_code == 200
        assert client.get("/settings/pricing").json()[0]["hourly_rate"] == 75
        audit_rows = client.get("/audit/").json()
        assert audit_rows[0]["action"] == "PRICING_RULE_UPDATED"
        assert audit_rows[0]["details"]["before"]["hourly_rate"] == 50

    engine.dispose()
