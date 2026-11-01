from datetime import datetime, timedelta
from decimal import Decimal
from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import current_user
from app.api.v1.endpoints import payments
from app.core.database import Base, get_db
from app.models.all_models import (
    ActivityLog,
    ParkingRecord,
    ParkingSlot,
    ParkingStatus,
    Payment,
    PaymentMethod,
    PaymentStatus,
    SlotStatus,
    User,
    Role,
    Vehicle,
    VehicleCategory,
    WalletPaymentSubmission,
)


def build_payment_client(role_name="ADMIN"):
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
        role = Role(role_name=role_name, description="Wallet payment test")
        db.add(role)
        db.flush()
        user = User(
            username="wallet-test",
            email="wallet-test@example.test",
            password_hash="not-used",
            full_name="Wallet Test",
            role_id=role.role_id,
        )
        category = VehicleCategory(category_name="CAR")
        db.add_all((user, category))
        db.flush()
        vehicle = Vehicle(
            plate_number="TEST 123",
            normalized_plate="TEST 123",
            category_id=category.category_id,
        )
        slot = ParkingSlot(
            slot_number="W01",
            category_id=category.category_id,
            status=SlotStatus.OCCUPIED,
        )
        db.add_all((vehicle, slot))
        db.flush()
        slot.current_vehicle_id = vehicle.vehicle_id
        record = ParkingRecord(
            vehicle_id=vehicle.vehicle_id,
            slot_id=slot.slot_id,
            entry_time=datetime.utcnow() - timedelta(hours=2),
            exit_time=datetime.utcnow(),
            status=ParkingStatus.PARKED,
        )
        db.add(record)
        db.flush()
        payment = Payment(
            record_id=record.record_id,
            total_duration_minutes=120,
            gross_amount=Decimal("100.00"),
            discount_amount=Decimal("0.00"),
            net_amount=Decimal("100.00"),
            payment_method=PaymentMethod.CASH,
            payment_status=PaymentStatus.PENDING,
        )
        db.add(payment)
        db.commit()
        record_id = record.record_id

    app = FastAPI()
    app.include_router(payments.router, prefix="/payments")
    app.dependency_overrides[get_db] = test_db
    app.dependency_overrides[current_user] = lambda: SimpleNamespace(
        user_id=1,
        role=SimpleNamespace(role_name=role_name),
    )
    return engine, factory, TestClient(app), record_id


def test_wallet_submission_stays_pending_and_duplicate_transaction_is_rejected(monkeypatch):
    engine, factory, client, record_id = build_payment_client()
    monkeypatch.setattr(payments.settings, "BKASH_PERSONAL_NUMBER", "01900000000")
    with client:
        response = client.post(
            f"/payments/personal-wallet/{record_id}/submit",
            json={
                "method": "BKASH_PERSONAL",
                "transaction_id": "TXN-unique-001",
                "amount": "100.00",
                "payer_wallet_masked": "01****1234",
            },
        )
        assert response.status_code == 201
        assert response.json()["status"] == "PENDING_VERIFICATION"
        assert "manual verification" in response.json()["message"].lower()

        another_pending = client.post(
            f"/payments/personal-wallet/{record_id}/submit",
            json={
                "method": "BKASH_PERSONAL",
                "transaction_id": "TXN-another-pending",
                "amount": "100.00",
            },
        )
        assert another_pending.status_code == 409

        duplicate = client.post(
            f"/payments/personal-wallet/{record_id}/submit",
            json={
                "method": "BKASH_PERSONAL",
                "transaction_id": "TXN-unique-001",
                "amount": "100.00",
            },
        )
        assert duplicate.status_code == 409

        wrong_amount = client.post(
            f"/payments/personal-wallet/{record_id}/submit",
            json={
                "method": "NAGAD_PERSONAL",
                "transaction_id": "TXN-wrong-amount",
                "amount": "99.00",
            },
        )
        assert wrong_amount.status_code == 422
        with factory() as db:
            assert db.query(Payment).one().payment_status == PaymentStatus.PENDING
            assert db.query(ParkingSlot).one().status == SlotStatus.OCCUPIED
            assert db.query(WalletPaymentSubmission).count() == 1
    engine.dispose()


def test_only_authorized_admin_can_verify_and_slot_releases_after_approval(monkeypatch):
    engine, factory, client, record_id = build_payment_client()
    monkeypatch.setattr(payments.settings, "NAGAD_PERSONAL_NUMBER", "01900000000")
    with client:
        submitted = client.post(
            f"/payments/personal-wallet/{record_id}/submit",
            json={
                "method": "NAGAD_PERSONAL",
                "transaction_id": "NAGAD-TXN-8899",
                "amount": "100.00",
            },
        )
        assert submitted.status_code == 201
        submission_id = submitted.json()["submission_id"]
        assert len(client.get("/payments/personal-wallet/pending").json()) == 1

        rejected = client.post(
            f"/payments/personal-wallet/submissions/{submission_id}/review",
            json={"decision": "REJECTED", "note": "Could not confirm in receiving wallet."},
        )
        assert rejected.status_code == 200
        assert rejected.json()["payment_status"] == "PENDING"
        with factory() as db:
            assert db.query(ParkingSlot).one().status == SlotStatus.OCCUPIED
            assert db.query(ParkingRecord).one().status == ParkingStatus.PARKED
            submission = db.query(WalletPaymentSubmission).one()
            assert submission.verified_by == 1
            assert submission.status == "REJECTED"

        assert client.post(
            f"/payments/personal-wallet/submissions/{submission_id}/review",
            json={"decision": "VERIFIED", "note": "Duplicate review should fail."},
        ).status_code == 409

        second = client.post(
            f"/payments/personal-wallet/{record_id}/submit",
            json={
                "method": "NAGAD_PERSONAL",
                "transaction_id": "NAGAD-TXN-9900",
                "amount": "100.00",
            },
        )
        assert second.status_code == 201
        approved = client.post(
            f"/payments/personal-wallet/submissions/{second.json()['submission_id']}/review",
            json={"decision": "VERIFIED", "note": "Matched to the receiving wallet history."},
        )
        assert approved.status_code == 200
        assert approved.json()["payment_status"] == "PAID"
        with factory() as db:
            assert db.query(ParkingSlot).one().status == SlotStatus.AVAILABLE
            assert db.query(ParkingRecord).one().status == ParkingStatus.COMPLETED
            assert db.query(Payment).one().payment_status == PaymentStatus.PAID
            assert db.query(ActivityLog).filter(
                ActivityLog.action == "PERSONAL_WALLET_PAYMENT_VERIFIED"
            ).count() == 1
    engine.dispose()


def test_wallet_config_must_be_present_and_review_is_admin_only(monkeypatch):
    engine, _factory, client, record_id = build_payment_client(role_name="OPERATOR")
    monkeypatch.setattr(payments.settings, "BKASH_PERSONAL_NUMBER", "")
    with client:
        config = client.get("/payments/config").json()
        assert config["personal_wallets"]["BKASH_PERSONAL"]["configured"] is False
        unconfigured = client.post(
            f"/payments/personal-wallet/{record_id}/submit",
            json={
                "method": "BKASH_PERSONAL",
                "transaction_id": "TXN-not-configured",
                "amount": "100.00",
            },
        )
        assert unconfigured.status_code == 503
        assert client.get("/payments/personal-wallet/pending").status_code == 403
    engine.dispose()
