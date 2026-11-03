# Final system verification

## Latest verification update — 2026-11-02

This checkout is **PARTIALLY READY**, not functionally complete or ready for a
production demonstration. This update records work and checks performed in the
latest session; it does not upgrade historical results into claims about
unexecuted tests.

| Area | Latest result | Evidence / limitation |
|---|---|---|
| MariaDB runtime | PASS | XAMPP MariaDB 10.4.32 was unresponsive at startup. A private filesystem safety copy of the active 177-file data directory was verified before restarting the single stalled process. The restarted server completed its MySQL protocol greeting and a live query succeeded. |
| Backend runtime | PASS | FastAPI root responded at `http://localhost:8000/` after startup against the live MariaDB database. |
| Frontend runtime | PASS | Vite returned HTTP 200 at `http://localhost:5173/`. |
| Existing administrator | PARTIAL | The database contains one active `SUPER_ADMIN`; its current password was not read or changed. Fresh password login was not tested with an owner-supplied credential. A protected existing browser session loaded the Payments route. |
| Administrator recovery | PASS (isolated tests) | Added hidden-input bootstrap/reset CLI. It refuses duplicate admin creation, validates password strength and history, audits changes, sets token-version invalidation, and can require rotation. Live reset was not run because no new password was supplied through a secure terminal prompt. |
| Blocklist enforcement | PASS (automated tests) | Active blacklist now blocks vehicle registration, direct entry, reservation creation, and reservation check-in if blacklisted after booking. Block attempts are audited and notified; test coverage confirms no session or slot allocation. |
| Personal-wallet configuration | PASS (configuration/UI check) | Both personal receiver settings are loaded. The real Payments page displayed the configured bKash receiver and real pending payment rows. No transfer was made and no transaction was approved or rejected. |
| Payment-review interaction | PASS (browser UI check) | Replaced `window.prompt()` review flow with an accessible native review dialog. Opened and cancelled the dialog without changing a payment. |
| Mobile layout | PARTIAL | Payments page checked at a 375px configured viewport; browser content width was 360px with no document horizontal overflow. Other pages and viewport sizes were not checked in this run. |
| Backend regression suite | PASS | `python -m pytest -q`: 57 passed, 2 skipped. The skips remain database integration tests and are not represented as passing. |
| Frontend quality | PASS | `npm run lint` and `npm run build` both passed after the Payments dialog change. |
| Route/API matrix | PARTIAL | Every route declared in `frontend/src/App.tsx` is listed in [the page/API matrix](./PAGE_API_INTEGRATION_MATRIX.md); routes not exercised in a live browser are explicitly marked NOT TESTED or PARTIAL. |
| Live payment workflow | NOT TESTED | No real transfer or wallet-history review was performed. Personal wallet submission remains pending until an administrator manually verifies it. |
| Fresh authentication and password rotation | NOT TESTED | Existing account password was not disclosed or reset in this run; use the local hidden-input CLI to recover access safely. |

MariaDB was restarted with its existing XAMPP configuration and active data
directory. The private safety copy is not part of the project source package.
The earlier HTTP/CORS check against `127.0.0.1` used an origin not in the
configured allowlist; the supported `http://localhost:5173` preflight returned
HTTP 200 with the expected CORS header.

## Verified in this workspace

- Backend regression suite: **57 passed, 2 skipped**. The skips are opt-in
  database tests; two MariaDB concurrency tests were separately run against an
  isolated disposable test database and passed.
- Backend Python compilation and frontend TypeScript/production build passed.
- Personal-wallet payment tests: **3 passed**. A wallet submission stays
  pending, does not release the occupied parking slot, and only an authorized
  administrator can approve or reject it. Pending submissions require manual
  comparison against the receiving wallet history; no provider verification is
  performed.
- PDF history test generated a PDF that was parsed and checked for expected
  report content.
- A protected database backup was restored into a separate disposable database.
  The 17 table names, row counts, primary-/foreign-key metadata counts, and a
  representative joined query matched. The disposable restore database was
  cleaned up; the original backup was preserved.
- The administrator password-rotation migration was applied after a protected
  backup, flagging the existing administrator account without recreating it.
  Focused rotation tests passed, including old-token invalidation.
- AI readiness diagnostics ran and reported missing model weights and OCR
  dependencies/language data.

## Deployment notes

- Existing databases receive new ORM tables through backend startup
  `create_all`. For manually managed MySQL/MariaDB installs, back up first and
  apply the numbered SQL migrations in `database/migrations/`.
- Personal bKash/Nagad receiving numbers are optional environment settings.
  Blank settings disable the corresponding personal-wallet option. The
  transaction workflow is a manual review process, not an official merchant
  integration.
- The production XAMPP database is separate from the disposable restore and
  concurrency databases. The concurrency test database may remain empty because
  database-drop permission was unavailable.

## Not verified or still incomplete

- No trained detection weights, representative footage, or physical USB/IP/RTSP
  camera were available. Shared capture and persistent camera-health features,
  ROI editing, and video-derived occupancy remain incomplete.
- No merchant credentials or public HTTPS callback were available for
  provider-backed payment testing.
- Activity logging is not tamper-evident and has no external immutable
  retention.
- The tested PDF is parking-session history only; comprehensive analytics
  remain incomplete.
- Docker CLI was unavailable, so container configuration and runtime were not
  exercised.

See [the full technical audit](../FINAL_TECHNICAL_AUDIT_REPORT.md) for the
evidence table and remaining recommendations.
