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
