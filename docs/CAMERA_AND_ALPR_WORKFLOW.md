# Camera and ALPR Workflow

## Cameras

Default cameras:

| Camera | Role | Location |
|---|---|---|
| ENTRY-01 | ENTRY | Main Entry Gate |
| EXIT-01 | EXIT | Main Exit Gate |
| ZONE-A | PARKING_ZONE | Parking Zone A |

Admins can add, edit and remove cameras from Camera Management.

## Entry flow

`ENTRY-01` → ALPR → Bangla/English OCR → plate normalization → blacklist check → vehicle lookup → automatic category suggestion → slot assignment → parking record.

## Exit flow

`EXIT-01` → ALPR/manual plate entry → active parking lookup → fee calculation → payment → checkout → slot release.

## Parking zone

`ZONE-A` is used for parking-area monitoring and can be extended to `ZONE-B`, `ZONE-C`, etc.

## Browser camera limitation

A raw RTSP URL is not automatically browser-playable. For live browser video, use a camera gateway that converts RTSP into WebRTC/HLS or use a backend OpenCV/FFmpeg capture service. The project keeps the stream URL in the database so the source can be configured without changing business logic.
