# Live Camera Sidebar

The dashboard includes a right-side live camera panel for configured `ENTRY`, `EXIT`, and `PARKING_ZONE` cameras.

## Architecture

Camera/RTSP/USB/local video -> FastAPI + OpenCV -> browser-compatible MJPEG -> React sidebar.

A browser should not be pointed directly at an `rtsp://` URL. Configure the RTSP/HTTP source in Camera Management; the backend opens the source and exposes an MJPEG stream endpoint for the web UI.

## Required demo cameras

- `ENTRY-01` — `ENTRY` — Main Entry Gate
- `EXIT-01` — `EXIT` — Main Exit Gate
- `ZONE-A` — `PARKING_ZONE` — Parking Zone A

## Browser authentication

The dashboard requests a camera-scoped stream ticket after normal API authentication because an HTML `<img>` cannot attach an Authorization header. Tickets expire after 60 seconds and only authorize the camera they were issued for; the long-lived access token is not put in the stream URL. The actual camera credentials stay in the database/server-side configuration.

The stream endpoint still opens a camera source per viewer. For production deployment with multiple simultaneous viewers, use a shared camera capture service and preferably WebRTC/HLS. The current pipeline does not report vehicle detection unless a compatible trained detector is present.
