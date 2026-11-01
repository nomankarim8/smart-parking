import ipaddress
import re
from pathlib import Path
from urllib.parse import urlsplit

from cryptography.fernet import Fernet, InvalidToken

from app.core.config import settings
from app.models.all_models import CameraType
from app.services.media import camera_demo_root, demo_video_root, is_within

ENCRYPTED_PREFIX = "encrypted:v1:"


def validate_camera_source(camera_type: CameraType, source: str | None) -> str | None:
    if source is None or not source.strip():
        return None

    value = source.strip()
    if any(ord(character) < 32 for character in value):
        raise ValueError("Camera source contains unsupported characters.")

    if camera_type == CameraType.USB:
        if not re.fullmatch(r"\d{1,3}", value) or int(value) > settings.CAMERA_MAX_USB_INDEX:
            raise ValueError("USB source must be an allowed local device index.")
        return value

    if camera_type in (CameraType.UPLOAD, CameraType.DEMO):
        path = Path(value)
        if not path.is_absolute():
            path = demo_video_root() / path
        try:
            resolved = path.resolve(strict=True)
        except (OSError, RuntimeError) as exc:
            raise ValueError("Configured local video source is unavailable.") from exc
        permitted = (
            camera_demo_root(),
            demo_video_root(),
        )
        if not resolved.is_file() or not any(is_within(resolved, root) for root in permitted):
            raise ValueError("Local video sources must be inside an approved demo-video directory.")
        return str(resolved)

    parsed = urlsplit(value)
    expected_schemes = {
        CameraType.IP: {"http", "https"},
        CameraType.RTSP: {"rtsp", "rtsps", "http", "https"},
    }
    if parsed.scheme.lower() not in expected_schemes.get(camera_type, set()):
        raise ValueError("Camera source uses an unsupported protocol.")
    if not parsed.hostname or parsed.fragment:
        raise ValueError("Camera source must include a valid host and cannot include a fragment.")
    try:
        parsed.port
    except ValueError as exc:
        raise ValueError("Camera source has an invalid port.") from exc

    host = parsed.hostname.lower().rstrip(".")
    if not _host_is_allowed(host):
        raise ValueError("Camera host is not in the administrator-configured allowlist.")
    return value


def encrypt_camera_source(source: str | None) -> str | None:
    if source is None or not source.lower().startswith(("rtsp://", "rtsps://", "http://", "https://")):
        return source
    if source.startswith(ENCRYPTED_PREFIX):
        return source
    try:
        token = _fernet().encrypt(source.encode("utf-8")).decode("ascii")
    except ValueError as exc:
        raise ValueError("Configure CAMERA_CREDENTIALS_KEY before saving network camera sources.") from exc
    return ENCRYPTED_PREFIX + token


def decrypt_camera_source(source: str | None) -> str | None:
    if source is None or not source.startswith(ENCRYPTED_PREFIX):
        return source
    try:
        return _fernet().decrypt(source[len(ENCRYPTED_PREFIX):].encode("ascii")).decode("utf-8")
    except (InvalidToken, UnicodeDecodeError, ValueError) as exc:
        raise ValueError("Saved camera source cannot be decrypted; verify CAMERA_CREDENTIALS_KEY.") from exc


def _fernet() -> Fernet:
    key = settings.CAMERA_CREDENTIALS_KEY
    if not key:
        raise ValueError("Camera credential encryption is not configured.")
    try:
        return Fernet(key.encode("ascii"))
    except (ValueError, UnicodeEncodeError) as exc:
        raise ValueError("CAMERA_CREDENTIALS_KEY must be a valid Fernet key.") from exc


def _host_is_allowed(host: str) -> bool:
    allowlist = settings.CAMERA_ALLOWED_HOST_SET
    if host in allowlist:
        return True
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        return False

    for entry in allowlist:
        try:
            if address in ipaddress.ip_network(entry, strict=False):
                return True
        except ValueError:
            continue
    return False
