import pytest

from app.core.config import Settings


def test_production_rejects_missing_or_known_weak_signing_secret():
    for secret in ("", "change-me", "replace-with-a-long-random-secret", "too-short"):
        configuration = Settings(APP_ENV="production", SECRET_KEY=secret)
        with pytest.raises(RuntimeError, match="SECRET_KEY"):
            configuration.validate_security_configuration()


def test_production_accepts_long_unique_signing_secret():
    configuration = Settings(APP_ENV="production", SECRET_KEY="unique-random-test-secret-value-0123456789")
    configuration.validate_security_configuration()


def test_weak_secret_is_only_accepted_in_explicit_development_mode():
    configuration = Settings(APP_ENV="development", SECRET_KEY="change-me")
    configuration.validate_security_configuration()

    with pytest.raises(RuntimeError, match="APP_ENV"):
        Settings(APP_ENV="staging", SECRET_KEY="unique-random-test-secret-value-0123456789").validate_security_configuration()
