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

The dashboard uses an already-issued JWT as a stream query token because an HTML `<img>` cannot attach an Authorization header. The actual camera credentials stay in the database/server-side configuration.

For production deployment, use HTTPS, short-lived stream tokens, and preferably WebRTC/HLS for large-scale multi-camera streaming.
