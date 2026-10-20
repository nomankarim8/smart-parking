import re
from datetime import datetime
from urllib.parse import quote

import httpx

from app.core.config import Settings, settings
from app.services.plate import BANGLA_DIGITS


class SmsDeliveryError(Exception):
    pass


def normalize_mobile_number(value: str) -> str:
    number = re.sub(r"[\s().-]", "", value.translate(BANGLA_DIGITS))
    if number.startswith("01") and len(number) == 11 and number.isdigit():
        return "+880" + number[1:]
    if number.startswith("8801") and len(number) == 13 and number.isdigit():
        return "+" + number
    if re.fullmatch(r"\+[1-9]\d{7,14}", number):
        return number
    raise ValueError("Enter a valid mobile number, such as 01XXXXXXXXX or +8801XXXXXXXXX.")


def send_reservation_confirmation(
    mobile_number: str,
    plate_number: str,
    slot_number: str,
    expires_at: datetime,
    config: Settings = settings,
) -> dict[str, str]:
    if not config.TWILIO_SMS_ENABLED:
        return {
            "status": "disabled",
            "message": "SMS is disabled. Configure Twilio to send confirmation messages.",
        }
    if not all(
        (
            config.TWILIO_ACCOUNT_SID,
            config.TWILIO_AUTH_TOKEN,
            config.TWILIO_FROM_NUMBER,
        )
    ):
        raise SmsDeliveryError(
            "Twilio is enabled but not configured. Set its account SID, auth token, and sender number."
        )

    try:
        recipient = normalize_mobile_number(mobile_number)
    except ValueError as exc:
        raise SmsDeliveryError(str(exc)) from exc

    expires = expires_at.strftime("%d %b %Y, %I:%M %p UTC")
    message = (
        f"Smart Parking reservation confirmed: {plate_number}, slot {slot_number}. "
        f"Your QR pass is valid until {expires}."
    )
    endpoint = (
        "https://api.twilio.com/2010-04-01/Accounts/"
        f"{quote(config.TWILIO_ACCOUNT_SID, safe='')}/Messages.json"
    )
    try:
        response = httpx.post(
            endpoint,
            auth=(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN),
            data={"From": config.TWILIO_FROM_NUMBER, "To": recipient, "Body": message},
            timeout=15.0,
        )
        response.raise_for_status()
        data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise SmsDeliveryError(
            "Twilio could not deliver the confirmation. Check the recipient, sender, account balance, and credentials."
        ) from exc

    sid = data.get("sid") if isinstance(data, dict) else None
    if not sid:
        raise SmsDeliveryError("Twilio accepted no message reference; delivery could not be confirmed.")
    return {"status": "queued", "message": "Confirmation SMS queued with Twilio."}
