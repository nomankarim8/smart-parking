from types import SimpleNamespace

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.deps import current_user
from app.api.v1.endpoints import alpr, cameras
from app.core.database import Base, get_db
from app.models.all_models import Camera, CameraRole, CameraStatus, CameraType, Role, User


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
        assert response.json()["stream_url"].startswith(str(tmp_path))
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
            files={"file": ("frame.jpg", b"mock-image-frame", "image/jpeg")},
        )
        assert response.status_code == 200
        assert response.json()["normalized_plate"] == "DHAKA METRO GA 12-3456"
        assert response.json()["input_image_url"] is None
        assert list(tmp_path.glob("*")) == []

    engine.dispose()
