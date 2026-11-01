# Windows Runbook

## Required

- Windows 10/11
- Python 3.11
- MySQL 8 or XAMPP MySQL
- Node.js 20+ (22 LTS is suitable)
- VS Code

## Verify tools

```powershell
py --version
python --version
node --version
npm --version
mysql --version
```

If `npm` is not recognized, install Node.js and restart VS Code/PowerShell so the Node.js install directory is on PATH.

## Backend

```powershell
cd smart-parking\backend
py -3.11 -m venv venv
venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
copy .env.example .env
python main.py
```

Open `http://localhost:8000/docs`.

If port `8000` is occupied by an old backend process, do not start a second
backend on that port. Use the project virtual environment on an available port,
then point the Vite dev server at it:

```powershell
# Backend terminal, from smart-parking\backend
..\venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8001

# Frontend terminal, from smart-parking\frontend
$env:VITE_API_URL = "http://127.0.0.1:8001/api/v1"
npm run dev -- --host 127.0.0.1
```

Run the backend through the project virtual environment so its installed
dependencies, including Windows `tzdata`, are available.

## Frontend

Open a second terminal:

```powershell
cd smart-parking\frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

## Database

Start XAMPP MySQL first, then execute `database/schema.sql` and `database/seeds.sql`.
Use the port shown in `C:\xampp\mysql\bin\my.ini`; this development machine uses `3302`.
Set `DB_PORT` in `backend\.env` to that value. Do not copy, rename, or delete a live
MySQL data directory to resolve a startup error. Take a logical `mysqldump` first.

The project includes protected Windows backup/restore scripts:

```powershell
# Verify XAMPP DB settings and connectivity without exporting data
.\scripts\backup_mysql.ps1 -CheckOnly

# Create a timestamped SQL backup outside public/static folders
.\scripts\backup_mysql.ps1

# Restore only a trusted project backup. This creates a safety backup first
# and requires the exact confirmation phrase before changing the database.
.\scripts\restore_mysql.ps1 -BackupFile .\backups\smart_parking_db_YYYYMMDD_HHMMSS.sql
```

Backups contain sensitive data. Keep the backup folder private and do not commit
or serve it from the frontend.

Dashboard and report date filters use `BUSINESS_TIMEZONE` (default
`Asia/Dhaka`) and UTC database timestamps. On Windows, install dependencies
from `backend\requirements.txt`; this includes the IANA `tzdata` package.

## Demo login

Username: `admin`
Password: `Admin@12345`

Change the password before any public deployment.

## Camera and model status

Demo video uploads are supported. Live stream tickets are camera-scoped and
short-lived. Camera status is not proof that AI inference is active. The AI
status endpoint is available at `/api/v1/alpr/status`; without a trained
`ai-models\plate_yolo.pt`, automatic plate localization and bounding boxes are
not enabled. A vehicle detector and camera-based parking-slot ROI occupancy
pipeline are not yet integrated. Do not treat demo video or sensor simulation
as evidence that those AI features are working.
