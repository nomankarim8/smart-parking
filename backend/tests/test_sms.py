from datetime import datetime

from app.core.config import Settings
from app.services import sms


def test_bangla_and_local_mobile_numbers_normalize_to_twilio_format():
    assert sms.normalize_mobile_number("০১৭১২৩৪৫৬৭৮") == "+8801712345678"
    assert sms.normalize_mobile_number("01712345678") == "+8801712345678"
    assert sms.normalize_mobile_number("+8801712345678") == "+8801712345678"


def test_reservation_confirmation_sends_twilio_sms(monkeypatch):
    config = Settings(
        TWILIO_SMS_ENABLED=True,
        TWILIO_ACCOUNT_SID="AC-test-account",
        TWILIO_AUTH_TOKEN="test-token",
        TWILIO_FROM_NUMBER="+15005550006",
    )
    captured = {}

    class Response:
        def raise_for_status(self):
            pass

        def json(self):
            return {"sid": "SM-test-message"}

    def mock_post(url, **kwargs):
        captured["url"] = url
        captured.update(kwargs)
        return Response()

    monkeypatch.setattr(sms.httpx, "post", mock_post)
    delivery = sms.send_reservation_confirmation(
        "01712345678",
        "DHAKA METRO GA 12-3456",
        "C01",
        datetime(2026, 10, 20, 15, 0),
        config,
    )

    assert delivery["status"] == "queued"
    assert captured["data"]["To"] == "+8801712345678"
    assert "DHAKA METRO GA 12-3456" in captured["data"]["Body"]
    assert "C01" in captured["data"]["Body"]
    assert captured["auth"] == ("AC-test-account", "test-token")
