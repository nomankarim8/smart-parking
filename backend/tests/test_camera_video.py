from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from jose import jwt
from PIL import Image
from io import BytesIO
from cryptography.fernet import Fernet

from app.api.deps import current_user
from app.api.v1.endpoints import alpr, cameras
from app.core.database import Base, get_db
from app.core.config import settings
from app.models.all_models import ActivityLog, Camera, CameraRole, CameraStatus, CameraType, Role, User
from app.services.camera_sources import decrypt_camera_source


def make_camera_client():
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
        username="camera-admin",
        role=SimpleNamespace(role_name="ADMIN"),
    )
    app = FastAPI()
    app.include_router(cameras.router, prefix="/cameras")
    app.include_router(alpr.router, prefix="/alpr")
    app.dependency_overrides[get_db] = get_test_db
    app.dependency_overrides[current_user] = lambda: staff
    return engine, session_factory, TestClient(app)


def seed_camera(session_factory):
    with session_factory() as db:
        role = Role(role_id=1, role_name="ADMIN", description="Test admin")
        db.add(role)
        db.add(
            User(
                user_id=1,
                username="camera-admin",
                email="camera-admin@example.local",
                password_hash="not-used",
                full_name="Camera Admin",
                role_id=1,
                is_active=True,
                role=role,
            )
        )
        camera = Camera(
            camera_name="ENTRY-01",
            location="Test gate",
            camera_role=CameraRole.ENTRY,
            camera_type=CameraType.DEMO,
            status=CameraStatus.UNKNOWN,
        )
        db.add(camera)
        db.commit()
        return camera.camera_id


def test_upload_video_sets_camera_demo_feed(monkeypatch, tmp_path):
    engine, session_factory, client = make_camera_client()
    camera_id = seed_camera(session_factory)
    monkeypatch.setattr(cameras, "CAMERA_VIDEO_DIR", tmp_path)

    class ReadableVideo:
        def __init__(self, _source):
            pass

        def read(self):
            return True, object()

        def release(self):
            pass

    monkeypatch.setattr(cameras.cv2, "VideoCapture", ReadableVideo)

    with client:
        response = client.post(
            f"/cameras/{camera_id}/upload-video",
            files={"file": ("parking.mp4", b"mock-video-content", "video/mp4")},
        )
        assert response.status_code == 200
        assert response.json()["camera_type"] == "UPLOAD"
        assert response.json()["status"] == "ONLINE"
        assert response.json()["stream_configured"] is True
        assert "stream_url" not in response.json()
        assert len(list(tmp_path.glob("*.mp4"))) == 1

    engine.dispose()


def test_video_upload_rejects_unapproved_file_type(tmp_path, monkeypatch):
    engine, session_factory, client = make_camera_client()
    camera_id = seed_camera(session_factory)
    monkeypatch.setattr(cameras, "CAMERA_VIDEO_DIR", tmp_path)

    with client:
        response = client.post(
            f"/cameras/{camera_id}/upload-video",
            files={"file": ("script.exe", b"not-video", "application/octet-stream")},
        )
        assert response.status_code == 400
        assert list(tmp_path.glob("*")) == []

    engine.dispose()


def test_alpr_video_frames_can_be_recognized_without_persisting_images(monkeypatch, tmp_path):
    engine, _session_factory, client = make_camera_client()
    monkeypatch.setattr(alpr, "UPLOAD_DIR", tmp_path)
    image = Image.new("RGB", (16, 16), "white")
    image_data = BytesIO()
    image.save(image_data, format="JPEG")
    monkeypatch.setattr(
        alpr.alpr_service,
        "recognize",
        lambda _data: {
            "input_image_url": None,
            "license_plate": "DHAKA METRO GA 12-3456",
            "normalized_plate": "DHAKA METRO GA 12-3456",
            "raw_text": "ঢাকা মেট্রো গ ১২-৩৪৫৬",
            "confidence": 0.95,
            "status": "AUTO_ACCEPTED",
            "verification_required": False,
            "detector": "test",
            "plate_box": None,
            "region_name": "DHAKA METRO",
            "class_bn": "গ",
            "class_code": "GA",
            "series_number": "12",
            "vehicle_number": "3456",
            "vehicle_category": "CAR",
            "suggested_category_id": 2,
            "ocr_language": "bn",
            "ocr_engine": "Tesseract",
        },
    )

    with client:
        response = client.post(
            "/alpr/detect?persist=false",
            files={"file": ("frame.jpg", image_data.getvalue(), "image/jpeg")},
        )
        assert response.status_code == 200
        assert response.json()["normalized_plate"] == "DHAKA METRO GA 12-3456"
        assert response.json()["input_image_url"] is None
        assert list(tmp_path.glob("*")) == []

    engine.dispose()


def test_camera_sources_are_allowlisted_encrypted_and_never_serialized(monkeypatch):
    engine, session_factory, client = make_camera_client()
    key = Fernet.generate_key().decode("ascii")
    monkeypatch.setattr(settings, "CAMERA_CREDENTIALS_KEY", key)
    monkeypatch.setattr(settings, "CAMERA_ALLOWED_HOSTS", "10.0.0.0/8")

    with client:
        response = client.post(
            "/cameras/",
            json={
                "camera_name": "ZONE-SECRET",
                "location": "Restricted zone",
                "camera_role": "PARKING_ZONE",
                "camera_type": "RTSP",
                "stream_url": "rtsp://camera-user:camera-password@10.2.3.4:554/live",
            },
        )
        assert response.status_code == 201
        assert response.json()["stream_configured"] is True
        assert "stream_url" not in response.json()
        assert b"camera-password" not in response.content

        with session_factory() as db:
            camera = db.query(Camera).filter_by(camera_name="ZONE-SECRET").one()
            assert camera.stream_url.startswith("encrypted:v1:")
            assert "camera-password" not in camera.stream_url
            assert decrypt_camera_source(camera.stream_url) == "rtsp://camera-user:camera-password@10.2.3.4:554/live"
            activity = db.query(ActivityLog).filter_by(action="CAMERA_CREATED").one()
            assert "camera-password" not in str(activity.details)

        listed = client.get("/cameras/")
        assert listed.status_code == 200
        assert b"camera-password" not in listed.content
        assert "stream_url" not in listed.json()[0]

    engine.dispose()


def test_camera_source_rejects_unallowlisted_host_and_unsupported_scheme():
    engine, _session_factory, client = make_camera_client()

    with client:
        unallowlisted = client.post(
            "/cameras/",
            json={
                "camera_name": "UNTRUSTED",
                "location": "Untrusted",
                "camera_role": "PARKING_ZONE",
                "camera_type": "RTSP",
                "stream_url": "rtsp://127.0.0.1:8000/private",
            },
        )
        assert unallowlisted.status_code == 422
        assert "allowlist" in unallowlisted.json()["detail"]

        unsupported = client.post(
            "/cameras/",
            json={
                "camera_name": "INVALID-SCHEME",
                "location": "Invalid",
                "camera_role": "PARKING_ZONE",
                "camera_type": "RTSP",
                "stream_url": "file:///C:/Windows/win.ini",
            },
        )
        assert unsupported.status_code == 422
        assert "protocol" in unsupported.json()["detail"]

    engine.dispose()


def test_alpr_media_is_private_and_stored_under_configured_directory(monkeypatch, tmp_path):
    engine, _session_factory, client = make_camera_client()
    monkeypatch.setattr(alpr, "UPLOAD_DIR", tmp_path)
    image_data = BytesIO()
    Image.new("RGB", (24, 24), "white").save(image_data, format="PNG")
    monkeypatch.setattr(
        alpr.alpr_service,
        "recognize",
        lambda _data: {
            "input_image_url": None,
            "license_plate": "",
            "normalized_plate": "",
            "raw_text": "",
            "confidence": 0.0,
            "status": "MANUAL_REQUIRED",
            "verification_required": True,
            "detector": "Manual verification",
        },
    )

    with client:
        detected = client.post(
            "/alpr/detect",
            files={"file": ("plate.png", image_data.getvalue(), "image/png")},
        )
        assert detected.status_code == 200
        media_url = detected.json()["input_image_url"]
        assert media_url.startswith("/api/v1/alpr/media/")
        media_name = media_url.rsplit("/", 1)[-1]
        assert (tmp_path / media_name).is_file()
        retrieved = client.get(f"/alpr/media/{media_name}")
        assert retrieved.status_code == 200
        assert retrieved.headers["cache-control"] == "private, no-store"
        assert client.get("/uploads/" + media_name).status_code == 404
        assert client.get("/alpr/media/..%2Fsecret.jpg").status_code == 404
        assert client.get("/alpr/media/" + "f" * 32 + ".jpg").status_code == 404

        client.app.dependency_overrides.pop(current_user)
        unauthorized = client.get(f"/alpr/media/{media_name}")
        assert unauthorized.status_code == 401

    engine.dispose()


def test_alpr_rejects_content_type_spoofed_non_image():
    engine, _session_factory, client = make_camera_client()
    with client:
        response = client.post(
            "/alpr/detect",
            files={"file": ("fake.jpg", b"not-an-image", "image/jpeg")},
        )
        assert response.status_code == 400
    engine.dispose()


def test_stream_requires_camera_scoped_short_lived_ticket(monkeypatch):
    engine, session_factory, client = make_camera_client()
    camera_id = seed_camera(session_factory)
    with session_factory() as db:
        camera = db.get(Camera, camera_id)
        camera.status = CameraStatus.ONLINE
        camera.camera_type = CameraType.USB
        camera.stream_url = "0"
        db.commit()
    monkeypatch.setattr(cameras.CameraStream, "frames", lambda _self: iter([b"frame"]))

    with client:
        ticket_response = client.post(f"/cameras/{camera_id}/stream-ticket")
        assert ticket_response.status_code == 200
        ticket = ticket_response.json()["ticket"]
        claims = jwt.get_unverified_claims(ticket)
        assert claims["scope"] == "camera:stream"
        assert claims["camera_id"] == camera_id
        assert claims["exp"] - claims["iat"] == 60

        invalid = client.get(
            f"/cameras/{camera_id + 1}/stream",
            params={"ticket": ticket},
        )
        assert invalid.status_code == 401

        stream = client.get(
            f"/cameras/{camera_id}/stream",
            params={"ticket": ticket},
        )
        assert stream.status_code == 200
        assert b"frame" in stream.content

    engine.dispose()


def test_alpr_status_reports_missing_models_without_claiming_detection():
    engine, _session_factory, client = make_camera_client()

    with client:
        response = client.get("/alpr/status")
        assert response.status_code == 200
        status = response.json()
        assert status["vehicle_detection"] is False
        assert status["plate_detector"]["status"] in {"MISSING", "LOAD_ERROR"}
        assert status["automatic_plate_localization"] is False

    engine.dispose()
