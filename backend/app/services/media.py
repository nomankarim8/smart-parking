from pathlib import Path

from app.core.config import settings


BACKEND_ROOT = Path(__file__).resolve().parents[2]


def configured_directory(value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = BACKEND_ROOT / path
    return path.resolve()


def media_root() -> Path:
    return configured_directory(settings.MEDIA_ROOT)


def camera_demo_root() -> Path:
    return media_root() / "camera_demos"


def demo_video_root() -> Path:
    return configured_directory(settings.DEMO_VIDEO_ROOT)


def is_within(path: Path, directory: Path) -> bool:
    try:
        path.resolve().relative_to(directory.resolve())
        return True
    except ValueError:
        return False
