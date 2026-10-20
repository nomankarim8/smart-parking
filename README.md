# Smart AI-Based Vehicle Parking Management System with ALPR

University-level full-stack CSE project using FastAPI, MySQL, React + TypeScript, OpenCV, EasyOCR and optional Ultralytics YOLO.

## Current modules

- JWT authentication and role checks
- Vehicle CRUD
- Category-aware parking slot allocation
- Entry/exit lifecycle
- Configurable fee rules with grace period and daily cap
- Payment record creation
- ALPR upload/OCR pipeline with confidence and manual verification status
- Optional trained YOLO plate detector
- Blacklist alerts and notifications
- Dashboard statistics
- Historical parking-demand forecast
- Parking history + CSV export
- Camera registry
- Reservation notifications and admin audit history
- Simulated parking-slot sensor events
- Demo payment approval/decline flow with printable receipts
- Docker Compose support
- pytest-ready backend test structure

## Quick start on Windows 

1. Start MySQL/XAMPP.
2. Run `database/schema.sql` and `database/seeds.sql`.
3. Open `backend/`, create/activate the virtual environment and run `pip install -r requirements.txt`.
4. Copy `backend/.env.example` to `backend/.env` and set your MySQL password.
5. Run `python main.py`.
6. Open another terminal in `frontend/` and run `npm install` then `npm run dev`.
7. Open `http://localhost:5173`.
8. Login with `admin` / `Admin@12345`.

See `docs/WINDOWS_RUNBOOK.md`, `docs/ALPR_MODEL_SETUP.md`, `docs/INSTALLATION.md` and `docs/USER_MANUAL.md`.

## Operations demo features

- **bKash/Nagad checkout:** vehicle exit creates a pending payment. Configure merchant sandbox credentials, a public HTTPS callback URL and gateway keys in `backend/.env`; payment completion is only recorded after the gateway is queried and the verified amount/currency match. See the provider configuration section below.
- **Reservation confirmation SMS:** reservation form collects a mobile number and queues a Twilio confirmation when configured. Bangladesh local numbers (`01...`) and Bengali digits are normalized to international `+880...` format. Without Twilio credentials, the reservation still succeeds and clearly reports that SMS is disabled.
- **CCTV monitoring + video demo:** upload an MP4/AVI/MOV/MKV/WebM clip (up to 100 MB) to a registered camera, then open **CCTV Monitor** and start ALPR scanning. The server loops the uploaded clip as a live MJPEG preview; sampled frames are OCR-processed without saving every frame. Bengali and English plates are normalized to English, and detections can be sent to Vehicle Entry for operator confirmation.
- **Demo payments:** only available when `PAYMENT_DEMO_ENABLED=true`; keep disabled when demonstrating provider-backed transactions.
- **Demand forecast:** the dashboard estimates hourly occupancy from parking sessions recorded over the previous 56 days. Predictions become more representative as history grows.
- **Notifications:** reservation confirmations, parking start/end, payment due, payment outcome, sensor simulation, and blacklist alerts appear in the Notifications page.
- **Sensor simulator:** Admin, Super Admin, or Operator can simulate free/occupied events on eligible slots. These simulated states do not create fake vehicle parking records.
- **Audit log and pricing:** Admin/Super Admin can review administrative activity and change category pricing in Settings. Fee, vehicle, camera, reservation, payment, and simulated sensor changes are recorded in the audit history.

Existing databases create the new `sensor_events` table automatically at backend startup. Fresh database installations also include it in `database/schema.sql`.

### bKash/Nagad sandbox setup

Copy the payment variables from `backend/.env.example` into `backend/.env`, then add credentials issued to your merchant account. Keep credentials and private keys server-side; never put them in frontend variables or commit them.

- Set `PAYMENT_MODE=sandbox` and retain the sandbox API URLs while testing.
- Start the backend on port `8000`, then expose it temporarily through a trusted HTTPS tunnel. For example, install Cloudflare Tunnel (`cloudflared`) and run `cloudflared tunnel --url http://localhost:8000`. Keep the tunnel terminal open while testing.
- Copy the generated HTTPS hostname into `PAYMENT_CALLBACK_BASE_URL`, with `/api/v1/payments` appended. For example: `PAYMENT_CALLBACK_BASE_URL=https://example.trycloudflare.com/api/v1/payments`. Do not add a trailing slash. A localhost callback is not reachable from the provider; a temporary tunnel hostname can change after restart.
- Set `PAYMENT_RETURN_URL` to the frontend payment result route.
- bKash needs the sandbox username, password, app key and app secret.
- Nagad needs the merchant ID/number, fixed server egress IPv4, Nagad public key and merchant private key. Preserve PEM line breaks or encode them as `\n`.
- Restart the backend after changing `.env`. Sign in and request `/api/v1/payments/config`; each provider's `configured` value should be `true` before its checkout button becomes available.
- Open **Payments** or **Vehicle Exit**, choose a provider, and complete its sandbox-hosted checkout using only the test account/data from the merchant-issued guide. The server verifies the transaction with the provider before issuing a receipt.
- A tunnel exposes the development API to the internet. Use a temporary test database, change the default credentials and `SECRET_KEY`, share the tunnel URL only with the provider/tester, and stop the tunnel as soon as testing is complete. Never use real customer data or real-money credentials in this setup.
- Nagad request/signature fields and callback parameters must match the current merchant-issued integration guide. Confirm them with that guide and sandbox credentials before treating Nagad checkout as verified or enabling live payments.
- For production, use credentials and HTTPS API endpoints explicitly issued for the merchant account. Do not switch `PAYMENT_MODE` or API URLs to live without provider approval and a public HTTPS callback.

### Twilio reservation SMS setup

- Create/configure a Twilio account and obtain its Account SID, Auth Token, and an SMS-capable Twilio sender number.
- Set `TWILIO_SMS_ENABLED=true`, `TWILIO_ACCOUNT_SID`, `TWILIO_AUTH_TOKEN`, and `TWILIO_FROM_NUMBER` in `backend/.env`, then restart the backend.
- Enter the customer's mobile number when creating a reservation. Bangladesh `01XXXXXXXXX` and Bengali-digit numbers are normalized to `+8801XXXXXXXXX`; international E.164 numbers are also accepted.
- The API reports `queued` when Twilio accepts the SMS request; this is not a delivery receipt. Trial accounts may only send to phone numbers verified with Twilio. If sending fails, the reservation remains valid and the operator receives a warning notification.
- Keep Twilio credentials server-side. Do not use real customer numbers in development or commit `.env`.

### CCTV and uploaded-video demo

- Add a camera in **Cameras**, select it in **Video input**, and upload a supported clip (maximum 100 MB). The clip is stored under `backend/uploads/camera_demos/`; the registered camera is switched to Upload/Online.
- Open **CCTV Monitor** to view the server-looped feed. Select **Start plate scan** to sample the live feed every four seconds and run the existing ALPR pipeline. Each detection is shown in normalized English text; **Use plate at entry** pre-fills Vehicle Entry, where an operator must verify and confirm entry.
- For CCTV/IP/RTSP sources, configure a stream URL that is reachable by the backend host, and set the camera online. USB camera sources may use a local device index such as `0`. Only use feeds you own or are authorized to monitor.
- Automatic accuracy depends on image quality, a compatible trained plate detector, and installed OCR engines/languages. Install Tesseract with both `eng` and `ben` language data to recognize Bengali-script plates. The system does not bypass operator confirmation for parking entry.

## Important

A generic or missing model is not treated as a real ALPR model. For real plate detection, supply a compatible trained `ai-models/plate_yolo.pt` and evaluate it on a representative held-out test set.

## Camera Management

Open **Cameras** in the dashboard. Three default demo endpoints are provided:

| Camera | Role | Location |
|---|---|---|
| ENTRY-01 | ENTRY | Main Entry Gate |
| EXIT-01 | EXIT | Main Exit Gate |
| ZONE-A | PARKING_ZONE | Parking Zone A |

Admins can add, edit, or remove cameras and configure USB/IP/RTSP/Upload/Demo sources. Existing installations can run `database/migration_camera_roles.sql` to add the new camera role field.

## Bangla + English ALPR

The ALPR pipeline now combines optional YOLO plate localization with EasyOCR (English) and Tesseract (Bengali/English). Bengali plate characters and Bengali digits are normalized to a canonical English searchable form. For example, `ঢাকা মেট্রো ল ১৭-৭৫৪৪` is parsed as `DHAKA METRO LA 17-7544`, with `LA` suggesting the MOTORCYCLE category. OCR results below the configurable confidence threshold remain in manual verification state.

Install Tesseract with `ben` and `eng` languages and see `docs/BANGLA_ENGLISH_ALPR_SETUP.md`.

## Fresh vs Existing Database

### Fresh installation

Run, in order:

1. `database/schema.sql`
2. `database/seeds.sql`

### Existing database from the older ZIP

Run once:

1. `database/migration_full_upgrade.sql`

Do not run the same `ALTER TABLE` migration repeatedly. It is intended as a one-time upgrade from the previous schema.

## ALPR prerequisites

For Bengali OCR on Windows, install Tesseract OCR with both `eng` and `ben` language data. A trained plate detector is also required for automatic localization of plates inside full vehicle images; place it at `ai-models/plate_yolo.pt`. Without a compatible trained model, the system still supports upload/manual verification but does not claim automatic plate localization.
