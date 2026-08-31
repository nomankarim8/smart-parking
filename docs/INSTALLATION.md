# Installation Guide\n\n## Windows + VS Code\n1. Install Python 3.11+, Node.js LTS, MySQL 8 / XAMPP MySQL, and Git.\n2. Open this folder in VS Code.\n3. Create `backend/.env` from `backend/.env.example`.\n4. In MySQL, run `database/schema.sql` and `database/seeds.sql`.\n5. Backend:\n   `cd backend`\n   `py -3.11 -m venv venv`\n   `venv\\Scripts\\activate`\n   `pip install -r requirements.txt`\n   `python main.py`\n6. Open `http://localhost:8000/docs`.\n7. Frontend in a second terminal:\n   `cd frontend`\n   `npm install`\n   `npm run dev`\n8. Open `http://localhost:5173`.\n\nDemo login is created by backend bootstrap: `admin / Admin@12345`. Change this password strategy before any real deployment.\n\n## ALPR model files\nPlace trained/compatible YOLO weights in `ai-models/plate_yolo.pt` and optionally `vehicle_yolo.pt`. Without weights, the project remains usable through the OCR/manual verification workflow and the dedicated demo path; it does not pretend that a missing trained model is real detection.\nEOF
cat > /mnt/data/smart-parking/docs/API_DOCUMENTATION.md <<'EOF'
# API Documentation\n\nSwagger is available at `http://localhost:8000/docs`.\n\nMain routes:\n- POST `/api/v1/auth/login`\n- GET `/api/v1/auth/me`\n- GET/POST/PUT/DELETE `/api/v1/vehicles`\n- GET `/api/v1/slots/`\n- POST `/api/v1/alpr/detect`\n- POST `/api/v1/parking/entry`\n- POST `/api/v1/parking/exit`\n- GET `/api/v1/parking/active`\n- GET `/api/v1/parking/history`\n- GET `/api/v1/dashboard/stats`\n- GET/POST/DELETE `/api/v1/blacklist`\n- GET/POST `/api/v1/cameras`\n- GET `/api/v1/reports/history.csv`\nEOF
cat > /mnt/data/smart-parking/docs/PROJECT_STRUCTURE.md <<'EOF'
# Project Structure\n\n`backend/app/ai` contains ALPR processing, `services` contains business rules, `api` exposes HTTP routes, `models` contains SQLAlchemy entities, and `schemas` contains validated request/response contracts.\n\n`frontend/src` contains the React presentation layer. `database/` contains reproducible schema and seed SQL. `docs/` contains academic/technical documentation.\nEOF
cat > /mnt/data/smart-parking/docs/ALPR_MODEL_SETUP.md <<'EOF'
# ALPR Model Setup\n\nThe ALPR layer is deliberately model-agnostic. `app/services/alpr.py` loads EasyOCR when available and a YOLO plate detector when `ai-models/plate_yolo.pt` exists.\n\nFor the final university demonstration, use a trained license-plate detector appropriate for the camera geometry and a representative validation set. Report precision/recall and OCR accuracy from your own test set instead of claiming a universal accuracy percentage.\nEOF
cat > /mnt/data/smart-parking/backend/tests/test_billing.py <<'EOF'
from datetime import datetime,timedelta
from app.services.billing import calculate

def test_grace_period_returns_zero(db=None):
    class Q:
        def filter(self,*a,**k): return self
        def first(self): return None
    class D:
        def query(self,*a,**k): return Q()
    r=calculate(D(),2,datetime(2026,1,1,10,0),datetime(2026,1,1,10,10))
    assert r['amount']==0

def test_hour_rounding():
    class Q:
        def filter(self,*a,**k): return self
        def first(self): return type('R',(),{'hourly_rate':50,'grace_period_minutes':15,'min_charge':50,'daily_max_charge':500})()
    class D:
        def query(self,*a,**k): return Q()
    r=calculate(D(),2,datetime(2026,1,1,10,0),datetime(2026,1,1,11,16))
    assert r['amount']==100
