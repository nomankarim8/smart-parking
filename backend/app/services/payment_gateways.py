import base64
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation
import json
import secrets
from threading import Lock
from urllib.parse import urlparse
from zoneinfo import ZoneInfo

import httpx
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

from app.core.config import Settings, settings
from app.models.all_models import GatewayPayment

_bkash_token: str | None = None
_bkash_token_expires_at = datetime.min
_bkash_token_lock = Lock()


class GatewayError(Exception):
    pass


def _base_url(config: Settings, provider: str) -> str:
    return (
        config.BKASH_BASE_URL
        if provider == "BKASH"
        else config.NAGAD_BASE_URL
    ).rstrip("/")


def gateway_is_configured(provider: str, config: Settings = settings) -> bool:
    if not config.PAYMENT_CALLBACK_BASE_URL:
        return False
    if provider == "BKASH":
        return all(
            (
                config.BKASH_USERNAME,
                config.BKASH_PASSWORD,
                config.BKASH_APP_KEY,
                config.BKASH_APP_SECRET,
            )
        )
    if provider == "NAGAD":
        return all(
            (
                config.NAGAD_MERCHANT_ID,
                config.NAGAD_MERCHANT_NUMBER,
                config.NAGAD_HOST_IP,
                config.NAGAD_PUBLIC_KEY,
                config.NAGAD_PRIVATE_KEY,
            )
        )
    return False


def _response_json(response: httpx.Response) -> dict:
    try:
        response.raise_for_status()
        data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise GatewayError("Payment provider did not return a valid response") from exc
    if not isinstance(data, dict):
        raise GatewayError("Payment provider returned an unexpected response")
    if data.get("statusCode") not in (None, "0000", "000"):
        message = data.get("statusMessage") or data.get("errorMessageEn")
        raise GatewayError(str(message or "Payment provider rejected the request"))
    return data


def _request_json(method: str, url: str, **kwargs) -> dict:
    try:
        with httpx.Client(timeout=30.0, follow_redirects=False) as client:
            response = client.request(method, url, **kwargs)
    except httpx.HTTPError as exc:
        raise GatewayError("Could not connect to payment provider") from exc
    return _response_json(response)


def _bkash_access_token(config: Settings) -> str:
    global _bkash_token, _bkash_token_expires_at
    with _bkash_token_lock:
        now = datetime.utcnow()
        if _bkash_token and now + timedelta(minutes=5) < _bkash_token_expires_at:
            return _bkash_token
        response = _request_json(
            "POST",
            f"{_base_url(config, 'BKASH')}/auth/grant-token",
            headers={
                "username": config.BKASH_USERNAME,
                "password": config.BKASH_PASSWORD,
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            json={
                "app_key": config.BKASH_APP_KEY,
                "app_secret": config.BKASH_APP_SECRET,
            },
        )
        token = response.get("id_token")
        if not token:
            raise GatewayError("bKash did not issue an access token")
        try:
            lifetime = int(response.get("expires_in", 3600))
        except (TypeError, ValueError):
            lifetime = 3600
        _bkash_token = str(token)
        _bkash_token_expires_at = now + timedelta(seconds=max(60, lifetime))
        return _bkash_token


def _bkash_headers(config: Settings) -> dict[str, str]:
    return {
        "Authorization": _bkash_access_token(config),
        "X-App-Key": config.BKASH_APP_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def _bkash_request(config: Settings, path: str, payload: dict) -> dict:
    return _request_json(
        "POST",
        f"{_base_url(config, 'BKASH')}/{path.lstrip('/')}",
        headers=_bkash_headers(config),
        json=payload,
    )


def _bkash_query(config: Settings, payment_id: str) -> dict:
    return _bkash_request(config, "/query/payment", {"paymentId": payment_id})


def _pem_public_key(value: str):
    normalized = value.replace("\\n", "\n").strip()
    if "-----BEGIN" not in normalized:
        normalized = f"-----BEGIN PUBLIC KEY-----\n{normalized}\n-----END PUBLIC KEY-----"
    try:
        return serialization.load_pem_public_key(normalized.encode("utf-8"))
    except (ValueError, TypeError) as exc:
        raise GatewayError("Nagad public key configuration is invalid") from exc


def _pem_private_key(value: str):
    normalized = value.replace("\\n", "\n").strip()
    if "-----BEGIN" not in normalized:
        normalized = f"-----BEGIN PRIVATE KEY-----\n{normalized}\n-----END PRIVATE KEY-----"
    try:
        return serialization.load_pem_private_key(
            normalized.encode("utf-8"),
            password=None,
        )
    except (ValueError, TypeError) as exc:
        raise GatewayError("Nagad private key configuration is invalid") from exc


def _nagad_headers(config: Settings) -> dict[str, str]:
    return {
        "Content-Type": "application/json",
        "X-KM-IP-V4": config.NAGAD_HOST_IP,
        "X-KM-Client-Type": "PC_WEB",
        "X-KM-Api-Version": "v-0.2.0",
    }


def _nagad_sign(payload: str, config: Settings) -> str:
    signature = _pem_private_key(config.NAGAD_PRIVATE_KEY).sign(
        payload.encode("utf-8"),
        padding.PKCS1v15(),
        hashes.SHA256(),
    )
    return base64.b64encode(signature).decode("ascii")


def _nagad_encrypt(payload: str, config: Settings) -> str:
    encrypted = _pem_public_key(config.NAGAD_PUBLIC_KEY).encrypt(
        payload.encode("utf-8"),
        padding.PKCS1v15(),
    )
    return base64.b64encode(encrypted).decode("ascii")


def _nagad_decrypt(payload: str, config: Settings) -> dict:
    try:
        decrypted = _pem_private_key(config.NAGAD_PRIVATE_KEY).decrypt(
            base64.b64decode(payload, validate=True),
            padding.PKCS1v15(),
        )
        value = json.loads(decrypted)
    except (ValueError, TypeError, json.JSONDecodeError) as exc:
        raise GatewayError("Could not verify Nagad checkout response") from exc
    if not isinstance(value, dict):
        raise GatewayError("Nagad returned an unexpected checkout response")
    return value


def _nagad_signed_data(data: dict, config: Settings) -> tuple[str, str]:
    sensitive = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
    return _nagad_encrypt(sensitive, config), _nagad_sign(sensitive, config)


def start_gateway_payment(
    gateway_payment: GatewayPayment,
    amount: Decimal,
    config: Settings = settings,
) -> dict[str, str]:
    if not gateway_is_configured(gateway_payment.provider, config):
        raise GatewayError(
            f"{gateway_payment.provider} sandbox is not configured. Add its merchant credentials and a public callback URL to backend/.env."
        )
    callback_base = config.PAYMENT_CALLBACK_BASE_URL.rstrip("/")
    callback_host = urlparse(callback_base)
    if callback_host.scheme != "https" and callback_host.hostname not in (
        "localhost",
        "127.0.0.1",
    ):
        raise GatewayError("Payment callback URL must use HTTPS")
    if gateway_payment.provider == "BKASH":
        return _start_bkash(gateway_payment, amount, config, callback_base)
    return _start_nagad(gateway_payment, amount, config, callback_base)


def _start_bkash(
    gateway_payment: GatewayPayment,
    amount: Decimal,
    config: Settings,
    callback_base: str,
) -> dict[str, str]:
    response = _bkash_request(
        config,
        "/payment/create",
        {
            "mode": "0011",
            "payerReference": f"Parking {gateway_payment.payment.record.vehicle.plate_number}"[:255],
            "callbackURL": f"{callback_base}/bkash/callback",
            "amount": f"{amount:.2f}",
            "currency": "BDT",
            "intent": "sale",
            "merchantInvoiceNumber": gateway_payment.invoice_number,
        },
    )
    payment_id = response.get("paymentID")
    checkout_url = response.get("bkashURL")
    if not payment_id or not checkout_url:
        raise GatewayError("bKash did not return a checkout URL")
    return {"provider_payment_id": str(payment_id), "checkout_url": str(checkout_url)}


def _start_nagad(
    gateway_payment: GatewayPayment,
    amount: Decimal,
    config: Settings,
    callback_base: str,
) -> dict[str, str]:
    now = datetime.now(ZoneInfo("Asia/Dhaka")).strftime("%Y%m%d%H%M%S")
    challenge = secrets.token_urlsafe(20)
    init_data = {
        "merchantId": config.NAGAD_MERCHANT_ID,
        "datetime": now,
        "orderId": gateway_payment.invoice_number,
        "challenge": challenge,
    }
    encrypted, signature = _nagad_signed_data(init_data, config)
    initialized = _request_json(
        "POST",
        f"{_base_url(config, 'NAGAD')}/check-out/initialize/{config.NAGAD_MERCHANT_ID}/{gateway_payment.invoice_number}",
        headers=_nagad_headers(config),
        json={
            "accountNumber": config.NAGAD_MERCHANT_NUMBER,
            "dateTime": now,
            "sensitiveData": encrypted,
            "signature": signature,
        },
    )
    response_signature = initialized.get("signature")
    response_sensitive_data = initialized.get("sensitiveData")
    if not response_signature or not response_sensitive_data:
        raise GatewayError("Nagad did not return a signed checkout response")
    try:
        _pem_public_key(config.NAGAD_PUBLIC_KEY).verify(
            base64.b64decode(response_signature, validate=True),
            response_sensitive_data.encode("ascii"),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
    except (ValueError, TypeError) as exc:
        raise GatewayError("Nagad checkout response signature is invalid") from exc
    response_data = _nagad_decrypt(response_sensitive_data, config)
    reference_id = response_data.get("paymentReferenceId")
    server_challenge = response_data.get("challenge")
    if not reference_id or not server_challenge:
        raise GatewayError("Nagad did not return a payment reference")

    completion_data = {
        "merchantId": config.NAGAD_MERCHANT_ID,
        "orderId": gateway_payment.invoice_number,
        "currencyCode": "050",
        "amount": f"{amount:.2f}",
        "challenge": server_challenge,
    }
    encrypted, signature = _nagad_signed_data(completion_data, config)
    completed = _request_json(
        "POST",
        f"{_base_url(config, 'NAGAD')}/check-out/complete/{reference_id}",
        headers=_nagad_headers(config),
        json={
            "dateTime": now,
            "sensitiveData": encrypted,
            "signature": signature,
            "merchantCallbackURL": f"{callback_base}/nagad/callback",
            "additionalMerchantInfo": {"recordId": gateway_payment.payment.record_id},
        },
    )
    checkout_url = completed.get("callBackUrl")
    if completed.get("status") != "Success" or not checkout_url:
        raise GatewayError("Nagad did not return a checkout URL")
    return {"provider_payment_id": str(reference_id), "checkout_url": str(checkout_url)}


def verify_gateway_payment(
    gateway_payment: GatewayPayment,
    callback_params: dict[str, str],
    config: Settings = settings,
) -> dict:
    if gateway_payment.provider == "BKASH":
        return _verify_bkash(gateway_payment, callback_params, config)
    return _verify_nagad(gateway_payment, callback_params, config)


def _verify_bkash(
    gateway_payment: GatewayPayment,
    callback_params: dict[str, str],
    config: Settings,
) -> dict:
    payment_id = callback_params.get("paymentID") or gateway_payment.provider_payment_id
    if not payment_id or payment_id != gateway_payment.provider_payment_id:
        raise GatewayError("bKash payment reference does not match this invoice")
    callback_status = callback_params.get("status", "").lower()
    result = None
    if callback_status == "success":
        try:
            result = _bkash_request(
                config,
                "/payment/execute",
                {"paymentId": payment_id},
            )
        except GatewayError:
            result = _bkash_query(config, payment_id)
    else:
        result = _bkash_query(config, payment_id)
    returned_invoice = str(
        result.get("merchantInvoiceNumber") or result.get("merchantInvoice") or ""
    )
    if returned_invoice and returned_invoice != gateway_payment.invoice_number:
        raise GatewayError("bKash verification invoice does not match this payment")
    return {
        "completed": result.get("transactionStatus") == "Completed",
        "transaction_reference": str(result.get("trxId") or payment_id),
        "amount": str(result.get("amount", "")),
        "currency": str(result.get("currency", "BDT")),
    }


def _verify_nagad(
    gateway_payment: GatewayPayment,
    callback_params: dict[str, str],
    config: Settings,
) -> dict:
    reference_id = (
        callback_params.get("payment_ref_id")
        or callback_params.get("paymentReferenceId")
        or callback_params.get("paymentRefId")
        or gateway_payment.provider_payment_id
    )
    if not reference_id or reference_id != gateway_payment.provider_payment_id:
        raise GatewayError("Nagad payment reference does not match this invoice")
    result = _request_json(
        "GET",
        f"{_base_url(config, 'NAGAD')}/verify/payment/{reference_id}",
        headers=_nagad_headers(config),
    )
    returned_invoice = result.get("orderId") or result.get("merchantInvoiceNumber")
    if returned_invoice and str(returned_invoice) != gateway_payment.invoice_number:
        raise GatewayError("Nagad verification invoice does not match this payment")
    return {
        "completed": result.get("status") == "Success",
        "transaction_reference": str(
            result.get("issuerPaymentRefNo") or result.get("paymentReferenceId") or reference_id
        ),
        "amount": str(result.get("amount", "")),
        "currency": str(result.get("currency", result.get("currencyCode", "050"))),
    }


def verified_amount_matches(amount: Decimal, result: dict) -> bool:
    try:
        returned_amount = Decimal(str(result.get("amount")))
    except (InvalidOperation, TypeError, ValueError):
        return False
    return returned_amount == amount
