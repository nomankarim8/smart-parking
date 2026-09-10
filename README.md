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
- Parking history + CSV export
- Camera registry
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
