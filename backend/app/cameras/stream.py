import time
from pathlib import Path
from typing import Generator, Union

import cv2


class CameraStream:
    """Read frames from RTSP/HTTP/USB/local video and emit MJPEG."""

    def __init__(self, source: Union[str, int]):
        self.source = source

    def _open(self):
        source = self.source
        if isinstance(source, str) and source.isdigit():
            source = int(source)
        return cv2.VideoCapture(source)

    def frames(self) -> Generator[bytes, None, None]:
        cap = self._open()
        if not cap.isOpened():
            raise RuntimeError(f"Unable to open camera source: {self.source}")

        try:
            try:
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            except Exception:
                pass

            while True:
                ok, frame = cap.read()
                if not ok:
                    # Loop local demo video files when they reach EOF.
                    if isinstance(self.source, str) and Path(self.source).exists():
                        cap.release()
                        cap = self._open()
                        if cap.isOpened():
                            continue
                    time.sleep(0.25)
                    continue

                height, width = frame.shape[:2]
                if width > 960:
                    scale = 960 / width
                    frame = cv2.resize(
                        frame,
                        (int(width * scale), int(height * scale)),
                        interpolation=cv2.INTER_AREA,
                    )

                ok, encoded = cv2.imencode(
                    ".jpg",
                    frame,
                    [int(cv2.IMWRITE_JPEG_QUALITY), 78],
                )
                if not ok:
                    continue

                yield (
                    b"--frame\r\n"
                    b"Content-Type: image/jpeg\r\n"
                    b"Cache-Control: no-cache\r\n\r\n"
                    + encoded.tobytes()
                    + b"\r\n"
                )
        finally:
            cap.release()
