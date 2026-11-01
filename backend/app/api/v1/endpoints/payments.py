from datetime import datetime
from decimal import Decimal
from enum import Enum
from urllib.parse import urlencode, urlparse, urlunparse, parse_qsl

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError

from app.api.deps import current_user, require_roles
from app.core.config import settings
from app.core.database import get_db
from app.models.all_models import (
    GatewayPayment,
    ParkingRecord,
    ParkingSlot,
    ParkingStatus,
    Payment,
    PaymentMethod,
    PaymentStatus,
    SlotStatus,
    WalletPaymentSubmission,
)
from app.services.activity import create_notification, record_activity
from app.services.payment_gateways import (
    GatewayError,
    gateway_is_configured,
    start_gateway_payment,
    verified_amount_matches,
    verify_gateway_payment,
)

router = APIRouter()


class PaymentProvider(str, Enum):
    BKASH = "BKASH"
    NAGAD = "NAGAD"


class CheckoutIn(BaseModel):
    provider: PaymentProvider


class DemoOutcome(str, Enum):
    APPROVED = "APPROVED"
    DECLINED = "DECLINED"


class DemoPaymentIn(BaseModel):
    outcome: DemoOutcome = DemoOutcome.APPROVED


class PersonalWalletMethod(str, Enum):
    BKASH_PERSONAL = "BKASH_PERSONAL"
    NAGAD_PERSONAL = "NAGAD_PERSONAL"


class WalletSubmissionIn(BaseModel):
    method: PersonalWalletMethod
    transaction_id: str = Field(min_length=4, max_length=120)
    amount: Decimal = Field(gt=0, max_digits=10, decimal_places=2)
    payer_wallet_masked: str | None = Field(default=None, min_length=5, max_length=32)


class WalletReviewIn(BaseModel):
    decision: str = Field(pattern="^(VERIFIED|REJECTED)$")
    note: str = Field(min_length=3, max_length=500)


def _complete_paid_parking_session(db: Session, payment: Payment) -> None:
    record = (
        db.query(ParkingRecord)
        .filter_by(record_id=payment.record_id)
        .with_for_update()
        .first()
    )
    if not record:
        raise HTTPException(409, "Parking session for this payment no longer exists.")
    if record.status == ParkingStatus.COMPLETED:
        return
    if record.status != ParkingStatus.PARKED or record.exit_time is None:
        raise HTTPException(409, "Parking session is not awaiting payment.")

    slot = (
        db.query(ParkingSlot)
        .filter_by(slot_id=record.slot_id)
        .with_for_update()
        .first()
    )
    if (
        not slot
        or slot.status != SlotStatus.OCCUPIED
        or slot.current_vehicle_id != record.vehicle_id
    ):
        raise HTTPException(
            409,
            "Parking slot state conflicts with the payment; ask an administrator to review it.",
        )

    record.status = ParkingStatus.COMPLETED
    slot.status = SlotStatus.AVAILABLE
    slot.current_vehicle_id = None


def receipt_data(payment: Payment) -> dict:
    record = payment.record
    gateway = next(
        (attempt for attempt in reversed(payment.gateway_payments) if attempt.status == "PAID"),
        None,
    )
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
        "payment_provider": gateway.provider if gateway else None,
        "payment_status": payment.payment_status.value,
        "transaction_reference": payment.transaction_reference,
        "payment_time": payment.payment_time.isoformat() if payment.payment_time else None,
    }


def _payment_return_url(record_id: int, result: str) -> str:
    parsed = urlparse(settings.PAYMENT_RETURN_URL)
    params = dict(parse_qsl(parsed.query))
    params.update({"record_id": str(record_id), "result": result})
    return urlunparse(parsed._replace(query=urlencode(params)))


def _provider_checkout_host_is_valid(provider: str, checkout_url: str) -> bool:
    parsed = urlparse(checkout_url)
    if parsed.scheme not in ("https", "http") or not parsed.hostname:
        return False
    host = parsed.hostname.lower()
    if provider == "BKASH":
        return host == "bka.sh" or host.endswith(".bka.sh")
    return host == "mynagad.com" or host.endswith(".mynagad.com")


def _record_provider_result(
    db: Session,
    attempt: GatewayPayment,
    payment: Payment,
    verified: dict,
    user_id: int | None = None,
) -> str:
    if verified.get("completed") is not True:
        attempt.status = "FAILED"
        payment.payment_status = PaymentStatus.FAILED
        create_notification(
            db,
            "Payment was not completed",
            f"{attempt.provider} did not complete payment for parking record #{payment.record_id}. The amount remains due.",
            "WARNING",
            user_id,
        )
        record_activity(
            db,
            user_id,
            "GATEWAY_PAYMENT_FAILED",
            "PAYMENT",
            payment.payment_id,
            {"provider": attempt.provider, "record_id": payment.record_id},
        )
        db.commit()
        return "failed"

    expected_currency = "BDT" if attempt.provider == "BKASH" else "050"
    if verified.get("currency") != expected_currency or not verified_amount_matches(
        Decimal(str(payment.net_amount)),
        verified,
    ):
        attempt.status = "REVIEW"
        create_notification(
            db,
            "Payment requires review",
            f"{attempt.provider} returned an amount or currency mismatch for parking record #{payment.record_id}.",
            "CRITICAL",
            user_id,
        )
        record_activity(
            db,
            user_id,
            "GATEWAY_PAYMENT_REVIEW",
            "PAYMENT",
            payment.payment_id,
            {"provider": attempt.provider, "record_id": payment.record_id},
        )
        db.commit()
        return "review"

    attempt.status = "PAID"
    attempt.provider_reference = verified["transaction_reference"][:120]
    payment.payment_status = PaymentStatus.PAID
    payment.payment_method = PaymentMethod.MOBILE_BANKING
    payment.payment_time = datetime.utcnow()
    payment.transaction_reference = attempt.provider_reference
    _complete_paid_parking_session(db, payment)
    create_notification(
        db,
        "Payment received",
        f"৳{float(payment.net_amount):.2f} received through {attempt.provider} for parking record #{payment.record_id}.",
        "INFO",
        user_id,
    )
    record_activity(
        db,
        user_id,
        "GATEWAY_PAYMENT_APPROVED",
        "PAYMENT",
        payment.payment_id,
        {
            "provider": attempt.provider,
            "record_id": payment.record_id,
            "reference": attempt.provider_reference,
        },
    )
    db.commit()
    return "success"


@router.get("/config")
def payment_configuration(_=Depends(current_user)):
    return {
        "mode": settings.PAYMENT_MODE.upper(),
        "providers": {
            provider: {
                "configured": gateway_is_configured(provider),
                "label": "bKash" if provider == "BKASH" else "Nagad",
            }
            for provider in ("BKASH", "NAGAD")
        },
        "demo_enabled": settings.PAYMENT_DEMO_ENABLED,
        "personal_wallets": {
            "BKASH_PERSONAL": {
                "configured": bool(settings.BKASH_PERSONAL_NUMBER),
                "receiver_number": settings.BKASH_PERSONAL_NUMBER or None,
            },
            "NAGAD_PERSONAL": {
                "configured": bool(settings.NAGAD_PERSONAL_NUMBER),
                "receiver_number": settings.NAGAD_PERSONAL_NUMBER or None,
            },
        },
    }

@router.post("/personal-wallet/{record_id}/submit", status_code=201)
def submit_personal_wallet_payment(
    record_id: int,
    payload: WalletSubmissionIn,
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
    if payment.payment_status not in (PaymentStatus.PENDING, PaymentStatus.FAILED):
        raise HTTPException(409, "Payment is not awaiting verification")
    if payment.record.status != ParkingStatus.PARKED or payment.record.exit_time is None:
        raise HTTPException(409, "Parking session is not awaiting exit payment")
    if Decimal(str(payment.net_amount)) != payload.amount:
        raise HTTPException(422, "Submitted amount must exactly match the server-calculated amount due")
    pending_submission = (
        db.query(WalletPaymentSubmission.submission_id)
        .filter_by(payment_id=payment.payment_id, status="PENDING_VERIFICATION")
        .first()
    )
    if pending_submission:
        raise HTTPException(409, "A wallet transaction is already waiting for verification")

    method = payload.method.value
    receiver = (
        settings.BKASH_PERSONAL_NUMBER
        if method == PersonalWalletMethod.BKASH_PERSONAL.value
        else settings.NAGAD_PERSONAL_NUMBER
    )
    if not receiver:
        raise HTTPException(503, f"{method} receiving number is not configured")
    transaction_id = payload.transaction_id.strip()
    if not transaction_id or not any(character.isalnum() for character in transaction_id):
        raise HTTPException(422, "A valid wallet transaction ID is required")
    if payload.payer_wallet_masked and not (
        "*" in payload.payer_wallet_masked and len(payload.payer_wallet_masked) >= 5
    ):
        raise HTTPException(422, "Payer wallet must be masked; do not submit a full wallet number")

    submission = WalletPaymentSubmission(
        payment_id=payment.payment_id,
        method=method,
        transaction_id=transaction_id,
        submitted_amount=payload.amount,
        payer_wallet_masked=payload.payer_wallet_masked,
        status="PENDING_VERIFICATION",
        submitted_by=user.user_id,
    )
    payment.payment_method = PaymentMethod.MOBILE_BANKING
    db.add(submission)
    record_activity(
        db,
        user.user_id,
        "PERSONAL_WALLET_PAYMENT_SUBMITTED",
        "PAYMENT",
        payment.payment_id,
        {"record_id": record_id, "method": method, "status": "PENDING_VERIFICATION"},
    )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "This wallet transaction ID has already been submitted") from exc
    db.refresh(submission)
    return {
        "submission_id": submission.submission_id,
        "record_id": record_id,
        "method": submission.method,
        "status": submission.status,
        "transaction_id": submission.transaction_id,
        "amount": float(submission.submitted_amount),
        "message": "Payment is pending manual verification. The parking slot remains occupied.",
    }

@router.get("/personal-wallet/pending")
def pending_wallet_payments(
    db: Session = Depends(get_db),
    _=Depends(require_roles("SUPER_ADMIN", "ADMIN")),
):
    rows = (
        db.query(WalletPaymentSubmission)
        .filter_by(status="PENDING_VERIFICATION")
        .order_by(WalletPaymentSubmission.submitted_at.asc())
        .limit(200)
        .all()
    )
    return [
        {
            "submission_id": row.submission_id,
            "record_id": row.payment.record_id,
            "plate_number": row.payment.record.vehicle.plate_number,
            "amount_due": float(row.payment.net_amount),
            "submitted_amount": float(row.submitted_amount),
            "method": row.method,
            "transaction_id": row.transaction_id,
            "payer_wallet_masked": row.payer_wallet_masked,
            "status": row.status,
            "submitted_at": row.submitted_at.isoformat(),
        }
        for row in rows
    ]

@router.post("/personal-wallet/submissions/{submission_id}/review")
def review_wallet_payment(
    submission_id: int,
    payload: WalletReviewIn,
    db: Session = Depends(get_db),
    user=Depends(require_roles("SUPER_ADMIN", "ADMIN")),
):
    submission_ref = db.get(WalletPaymentSubmission, submission_id)
    if not submission_ref:
        raise HTTPException(404, "Wallet payment submission not found")
    payment = (
        db.query(Payment)
        .filter_by(payment_id=submission_ref.payment_id)
        .with_for_update()
        .first()
    )
    submission = (
        db.query(WalletPaymentSubmission)
        .filter_by(submission_id=submission_id)
        .with_for_update()
        .first()
    )
    if not payment or not submission:
        raise HTTPException(404, "Wallet payment or parking payment no longer exists")
    if submission.status != "PENDING_VERIFICATION":
        raise HTTPException(409, "Wallet submission has already been reviewed")
    if Decimal(str(payment.net_amount)) != Decimal(str(submission.submitted_amount)):
        raise HTTPException(409, "Submitted payment no longer matches the amount due")

    submission.status = payload.decision
    submission.verified_by = user.user_id
    submission.verified_at = datetime.utcnow()
    submission.verification_note = payload.note.strip()
    if payload.decision == "VERIFIED":
        if payment.payment_status not in (PaymentStatus.PENDING, PaymentStatus.FAILED):
            raise HTTPException(409, "Parking payment is not awaiting verification")
        payment.payment_status = PaymentStatus.PAID
        payment.payment_method = PaymentMethod.MOBILE_BANKING
        payment.payment_time = submission.verified_at
        payment.transaction_reference = submission.transaction_id
        _complete_paid_parking_session(db, payment)
    record_activity(
        db,
        user.user_id,
        f"PERSONAL_WALLET_PAYMENT_{payload.decision}",
        "PAYMENT",
        payment.payment_id,
        {
            "record_id": payment.record_id,
            "method": submission.method,
            "amount": str(submission.submitted_amount),
            "transaction_id": submission.transaction_id,
            "note": submission.verification_note,
        },
    )
    db.commit()
    return {
        "submission_id": submission.submission_id,
        "record_id": payment.record_id,
        "status": submission.status,
        "payment_status": payment.payment_status.value,
        "receipt": receipt_data(payment) if payment.payment_status == PaymentStatus.PAID else None,
    }

@router.post("/{record_id}/checkout")
def create_checkout(
    record_id: int,
    payload: CheckoutIn,
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
        raise HTTPException(409, f"Payment cannot be retried from {payment.payment_status.value}")
    if Decimal(str(payment.net_amount)) <= Decimal("0"):
        raise HTTPException(409, "No payment is due for this parking record")
    if not gateway_is_configured(payload.provider.value):
        raise HTTPException(
            503,
            f"{payload.provider.value} sandbox is not configured. Set provider credentials and a public HTTPS callback URL in backend/.env.",
        )

    current_attempt = (
        db.query(GatewayPayment)
        .filter_by(payment_id=payment.payment_id)
        .order_by(GatewayPayment.gateway_payment_id.desc())
        .first()
    )
    if current_attempt and current_attempt.status in ("INITIATED", "REVIEW"):
        raise HTTPException(409, "A payment attempt is already in progress or requires review")

    attempt = GatewayPayment(
        payment_id=payment.payment_id,
        provider=payload.provider.value,
        invoice_number=f"SP{payment.payment_id:08d}{int(datetime.utcnow().timestamp())}",
        status="INITIATED",
    )
    payment.payment_method = PaymentMethod.MOBILE_BANKING
    db.add(attempt)
    db.commit()
    db.refresh(attempt)
    try:
        checkout = start_gateway_payment(
            attempt,
            Decimal(str(payment.net_amount)),
        )
    except GatewayError as exc:
        attempt.status = "FAILED"
        record_activity(
            db,
            user.user_id,
            "GATEWAY_CHECKOUT_FAILED",
            "PAYMENT",
            payment.payment_id,
            {"provider": attempt.provider, "reason": str(exc)},
        )
        db.commit()
        status_code = 502 if "not configured" not in str(exc) else 503
        raise HTTPException(status_code, str(exc)) from exc

    checkout_url = checkout["checkout_url"]
    if not _provider_checkout_host_is_valid(payload.provider.value, checkout_url):
        attempt.status = "FAILED"
        db.commit()
        raise HTTPException(502, "Payment provider returned an invalid checkout URL")
    attempt.provider_payment_id = checkout["provider_payment_id"]
    attempt.checkout_url = checkout_url
    record_activity(
        db,
        user.user_id,
        "GATEWAY_CHECKOUT_CREATED",
        "PAYMENT",
        payment.payment_id,
        {"provider": attempt.provider},
    )
    db.commit()
    return {
        "record_id": payment.record_id,
        "provider": attempt.provider,
        "checkout_url": attempt.checkout_url,
        "status": attempt.status,
    }


def _gateway_callback(
    provider: str,
    provider_payment_id: str,
    params: dict[str, str],
    db: Session,
) -> RedirectResponse:
    attempt = (
        db.query(GatewayPayment)
        .filter_by(provider=provider, provider_payment_id=provider_payment_id)
        .with_for_update()
        .first()
    )
    if not attempt:
        raise HTTPException(404, "Payment attempt not found")
    payment = db.query(Payment).filter_by(payment_id=attempt.payment_id).with_for_update().first()
    if not payment:
        raise HTTPException(404, "Payment record not found")
    if payment.payment_status == PaymentStatus.PAID:
        return RedirectResponse(
            _payment_return_url(payment.record_id, "success"),
            status_code=303,
        )
    try:
        verified = verify_gateway_payment(attempt, params)
    except GatewayError:
        return RedirectResponse(
            _payment_return_url(payment.record_id, "processing"),
            status_code=303,
        )
    result = _record_provider_result(db, attempt, payment, verified)
    return RedirectResponse(
        _payment_return_url(payment.record_id, result),
        status_code=303,
    )


@router.get("/bkash/callback")
def bkash_callback(
    payment_id: str = Query(alias="paymentID"),
    status: str = Query(default=""),
    db: Session = Depends(get_db),
):
    return _gateway_callback(
        "BKASH",
        payment_id,
        {"paymentID": payment_id, "status": status},
        db,
    )


@router.get("/nagad/callback")
def nagad_callback(request: Request, db: Session = Depends(get_db)):
    params = {str(key): str(value) for key, value in request.query_params.items()}
    reference = (
        params.get("payment_ref_id")
        or params.get("paymentReferenceId")
        or params.get("paymentRefId")
    )
    if not reference:
        raise HTTPException(400, "Nagad payment reference is missing")
    return _gateway_callback("NAGAD", reference, params, db)


@router.get("/{record_id}/status")
def payment_status(
    record_id: int,
    db: Session = Depends(get_db),
    _=Depends(current_user),
):
    payment = db.query(Payment).filter_by(record_id=record_id).first()
    if not payment:
        raise HTTPException(404, "Payment not found")
    attempt = (
        db.query(GatewayPayment)
        .filter_by(payment_id=payment.payment_id)
        .order_by(GatewayPayment.gateway_payment_id.desc())
        .first()
    )
    return {
        "record_id": record_id,
        "payment_status": payment.payment_status.value,
        "provider": attempt.provider if attempt else None,
        "gateway_status": attempt.status if attempt else None,
        "receipt": receipt_data(payment) if payment.payment_status == PaymentStatus.PAID else None,
    }


@router.post("/{record_id}/demo")
def complete_demo_payment(
    record_id: int,
    payload: DemoPaymentIn,
    db: Session = Depends(get_db),
    user=Depends(require_roles("SUPER_ADMIN", "ADMIN", "OPERATOR")),
):
    if not settings.PAYMENT_DEMO_ENABLED:
        raise HTTPException(403, "Demo payment completion is disabled")
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
        _complete_paid_parking_session(db, payment)
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


@router.post("/{record_id}/cash/confirm")
def confirm_cash_payment(
    record_id: int,
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
    if payment.payment_method != PaymentMethod.CASH:
        raise HTTPException(409, "Only cash payments can be confirmed at the exit desk.")
    if payment.payment_status == PaymentStatus.PAID:
        raise HTTPException(409, "Payment has already been completed")
    if payment.payment_status not in (PaymentStatus.PENDING, PaymentStatus.FAILED):
        raise HTTPException(409, f"Payment cannot be confirmed from {payment.payment_status.value}")

    payment.payment_status = PaymentStatus.PAID
    payment.payment_time = datetime.utcnow()
    payment.transaction_reference = f"CASH-{payment.payment_id}-{int(payment.payment_time.timestamp())}"
    _complete_paid_parking_session(db, payment)
    create_notification(
        db,
        "Cash payment received",
        f"৳{float(payment.net_amount):.2f} received for parking record #{record_id}.",
        "INFO",
        user.user_id,
    )
    record_activity(
        db,
        user.user_id,
        "CASH_PAYMENT_CONFIRMED",
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
