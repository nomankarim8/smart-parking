# Implementation and Verification Status

## Completed in this pass

- Fixed exit/payment ordering: a positive-fee exit now remains an active parking
  session and keeps its slot occupied until cash, demo, or provider payment is
  confirmed. Duplicate exit/payment attempts are rejected. No-charge exits can
  finish immediately.
- Added a staff cash-confirmation endpoint and audit event.
- Prevented an OCR result supplied with low confidence or an invalid plate
  structure from creating an entry. Manual entry remains available without an
  OCR confidence value.
- Replaced permanent access-token stream URLs with 60-second, camera-scoped
  stream tickets.
- Added an ALPR capability status endpoint and a truthful missing-model message
  in CCTV Monitor. A plate box is shown only when the detector actually returns
  coordinates.
- Changed seeded cameras with no configured source to `UNKNOWN`, rather than
  claiming they are online.
- Added Dhaka-business-timezone date windows to report summaries, CSV exports,
  and dashboard statistics. CSV cells beginning with spreadsheet formula
  characters are escaped.
- Added Windows MySQL backup and guarded restore scripts. Restore requires a
  pre-restore backup and explicit confirmation. Temporary MySQL credential
  files are restricted to the current Windows user.
- Added regression tests for payment/session safety, low-confidence entry,
  stream ticket scope/expiry, report date windows, and CSV formula escaping.

## Verification run

- XAMPP Apache configuration check: passed; HTTP `200` at `http://localhost/`.
- XAMPP MariaDB: running on the configured port `3302`, data directory
  `C:\xampp\mysql\data_recovered`, `innodb_force_recovery=0`.
- Database check: `smart_parking_db` is accessible; its existing rows and
  tables were retained.
- MySQL backup script `-CheckOnly`: passed against the configured database.
- Backend: `32 passed` with `python -m pytest tests -q` from `backend\`.
- Backend Python `compileall`: passed.
- Frontend: `npm run build` passed (TypeScript check plus Vite production build).
- Live app smoke checks: Apache, FastAPI root, and Vite frontend all returned
  HTTP `200`.

The test runner reports one upstream Starlette/httpx deprecation warning; it
does not fail the test suite.

## Not complete / external blockers

- No trained `plate_yolo.pt` or `vehicle_yolo.pt` weights are present. No model
  was fabricated or downloaded. Automatic vehicle/plate detection and
  camera-derived bounding boxes therefore remain disabled until appropriate
  licensed weights are supplied and evaluated on representative local data.
- The repository does not yet have parking-space ROI configuration or a
  temporally smoothed camera-occupancy worker. Slot occupancy continues to
  reflect parking transactions and the explicitly labelled sensor simulator;
  it is not inferred from video.
- CCTV Monitor still opens a camera source per viewer. A shared capture manager,
  bounded reconnect/health history, and a camera connection-test API are still
  needed for multi-viewer production deployment.
- Tesseract executable/language data and EasyOCR are not installed in this
  workstation's current Python environment. OCR results depend on installing
  those optional runtime requirements; Bengali and English OCR quality still
  needs test images and measured accuracy.
- Live camera hardware and payment/SMS merchant credentials were not available
  for end-to-end testing. Provider callback/production payment operation is
  not certified by the local test suite.
- Backup connectivity was tested, but an actual production-data restore was
  not run. Restore only a trusted backup into a disposable test database before
  relying on a recovery procedure.
- PDF reports, camera-health history, a frontend date-range picker, detection
  image retention controls, and comprehensive audit/search filters remain
  future work.

## Changed files

- `backend/app/api/v1/endpoints/parking.py`
- `backend/app/api/v1/endpoints/payments.py`
- `backend/app/api/v1/endpoints/cameras.py`
- `backend/app/api/v1/endpoints/alpr.py`
- `backend/app/core/security.py`
- `backend/app/core/config.py`
- `backend/app/services/alpr.py`
- `backend/app/services/bootstrap.py`
- `backend/app/services/reporting.py`
- `backend/app/api/v1/endpoints/dashboard.py`
- `backend/app/api/v1/endpoints/reports.py`
- `backend/requirements.txt`
- `backend/.env.example`
- `backend/tests/test_operations_features.py`
- `backend/tests/test_camera_video.py`
- `backend/tests/test_reporting.py`
- `frontend/src/components/CameraSidebar.tsx`
- `frontend/src/pages/Monitor.tsx`
- `frontend/src/pages/Exit.tsx`
- `frontend/src/pages/Dashboard.tsx`
- `scripts/mysql-tools.ps1`
- `scripts/backup_mysql.ps1`
- `scripts/restore_mysql.ps1`
- `docs/WINDOWS_RUNBOOK.md`
- `docs/LIVE_CAMERA_SIDEBAR.md`
