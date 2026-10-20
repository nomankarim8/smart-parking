from datetime import datetime
from decimal import Decimal
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import current_user, require_roles
from app.core.database import get_db
from app.models.all_models import (
    Payment,
    PaymentStatus,
    ParkingRecord,
    Vehicle,
)
from app.services.activity import create_notification, record_activity

router = APIRouter()


class DemoOutcome(str, Enum):
    APPROVED = "APPROVED"
    DECLINED = "DECLINED"


class DemoPaymentIn(BaseModel):
    outcome: DemoOutcome = DemoOutcome.APPROVED


def receipt_data(payment: Payment) -> dict:
    record = payment.record
    return {
        "receipt_number": f"SP-{payment.payment_id:08d}",
        "payment_id": payment.payment_id,
        "record_id": record.record_id,
        "plate_number": record.vehicle.plate_number,
        "slot": record.slot.slot_number,
        "entry_time": record.entry_time.isoformat(),
        "exit_time": record.exit_time.isoformat() if record.exit_time else None,
        "duration_minutes": payment.total_duration_minutes,
        "gross_amount": float(payment.gross_amount),
        "discount_amount": float(payment.discount_amount),
        "net_amount": float(payment.net_amount),
        "payment_method": payment.payment_method.value,
        "payment_status": payment.payment_status.value,
        "transaction_reference": payment.transaction_reference,
        "payment_time": payment.payment_time.isoformat() if payment.payment_time else None,
    }


@router.post("/{record_id}/demo")
def complete_demo_payment(
    record_id: int,
    payload: DemoPaymentIn,
    db: Session = Depends(get_db),
    user=Depends(require_roles("SUPER_ADMIN", "ADMIN", "OPERATOR")),
):
    payment = (
        db.query(Payment)
        .filter_by(record_id=record_id)
        .with_for_update()
        .first()
    )
    if not payment:
        raise HTTPException(404, "Payment is not due for this parking record")
    if payment.payment_status == PaymentStatus.PAID:
        raise HTTPException(409, "Payment has already been completed")
    if payment.payment_status not in (PaymentStatus.PENDING, PaymentStatus.FAILED):
        raise HTTPException(409, f"Payment cannot be completed from {payment.payment_status.value}")

    if payload.outcome == DemoOutcome.APPROVED:
        payment.payment_status = PaymentStatus.PAID
        payment.payment_time = datetime.utcnow()
        payment.transaction_reference = f"DEMO-{record_id}-{int(payment.payment_time.timestamp())}"
        create_notification(
            db,
            "Demo payment received",
            f"৳{float(payment.net_amount):.2f} received for parking record #{record_id}.",
            "INFO",
            user.user_id,
        )
        action = "DEMO_PAYMENT_APPROVED"
    else:
        payment.payment_status = PaymentStatus.FAILED
        payment.payment_time = None
        payment.transaction_reference = None
        create_notification(
            db,
            "Payment failed",
            f"Demo payment failed for parking record #{record_id}; ৳{float(payment.net_amount):.2f} remains due.",
            "WARNING",
            user.user_id,
        )
        action = "DEMO_PAYMENT_DECLINED"
    record_activity(
        db,
        user.user_id,
        action,
        "PAYMENT",
        payment.payment_id,
        {"record_id": record_id, "status": payment.payment_status.value},
    )
    db.commit()
    db.refresh(payment)
    return receipt_data(payment)


@router.get("/{record_id}/receipt")
def get_receipt(
    record_id: int,
    db: Session = Depends(get_db),
    _=Depends(current_user),
):
    payment = db.query(Payment).filter_by(record_id=record_id).first()
    if not payment:
        raise HTTPException(404, "Receipt not found")
    return receipt_data(payment)


@router.get("/due")
def due_payments(db: Session = Depends(get_db), _=Depends(current_user)):
    rows = (
        db.query(Payment)
        .filter(Payment.payment_status.in_([PaymentStatus.PENDING, PaymentStatus.FAILED]))
        .order_by(Payment.payment_id.desc())
        .limit(200)
        .all()
    )
    return [
        {
            "record_id": payment.record_id,
            "plate_number": payment.record.vehicle.plate_number,
            "amount_due": float(payment.net_amount),
            "payment_status": payment.payment_status.value,
        }
        for payment in rows
    ]
