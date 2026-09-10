# FINAL SETUP — Smart Parking ALPR

## A. New installation

1. Start MySQL/XAMPP.
2. Run `database/schema.sql`.
3. Run `database/seeds.sql`.
4. Copy `backend/.env.example` to `backend/.env`.
5. In `backend/`, create a Python 3.11 virtual environment and run `pip install -r requirements.txt`.
6. Install Tesseract OCR for Windows with `eng` and `ben` languages.
7. Run `python main.py`.
8. In `frontend/`, run `npm install` and `npm run dev`.
9. Open `http://localhost:5173`.
10. Login with `admin` / `Admin@12345`.

## B. Upgrade an older downloaded ZIP

Run only:

`database/migration_full_upgrade.sql`

Then replace/review the backend and frontend files included in this ZIP. Restart the backend and frontend.

## C. Camera defaults

- ENTRY-01 — Main Entry Gate — ENTRY — DEMO
- EXIT-01 — Main Exit Gate — EXIT — DEMO
- ZONE-A — Parking Zone A — PARKING_ZONE — DEMO

## D. Bengali + English plate examples

- `ঢাকা মেট্রো গ ১২-৩৪৫৬` → `DHAKA METRO GA 12-3456`
- `ঢাকা মেট্রো ল ১৭-৭৫৪৪` → `DHAKA METRO LA 17-7544`
- `ঢাকা মেট্রো ক ১১-১২৩৪` → `DHAKA METRO KA 11-1234`

The parser stores raw OCR plus normalized plate, region, Bengali class, English class code, series, vehicle number, OCR engine/language and suggested vehicle category.

## E. Important realism note

The application does not contain a made-up YOLO weight and does not claim 100% OCR accuracy. To enable true automatic plate localization from full vehicle images, provide a compatible trained plate detector at `ai-models/plate_yolo.pt` and evaluate it on held-out representative test data.
