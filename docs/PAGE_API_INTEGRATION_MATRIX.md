# Page/API integration verification matrix

This matrix lists the routes in `frontend/src/App.tsx` and their backend API
groups from `backend/app/api/v1/api.py`. “Not tested” means no real browser
interaction was executed for that route in the latest verification session;
the presence of an endpoint or a passing mocked/unit test is not evidence of a
live page workflow.

| Route | Page | Backend API group(s) | Real API/data evidence in latest run | UI/permission/responsive evidence | Status |
|---|---|---|---|---|---|
| `/login` | Login | `/auth/login`, `/auth/me` | Existing browser session loaded a protected route; fresh credential submission was not tested. | Login page rendered; 127.0.0.1 origin is not in CORS allowlist, localhost preflight passed. | PARTIAL |
| Protected password-rotation gate | Password rotation | `/auth/me`, `/auth/change-password` | Isolated backend rotation tests pass; live account was not reset. | Route behavior not tested in browser this run. | PARTIAL |
| `/` | Dashboard | `/dashboard`, `/cameras`, `/notifications` | Not tested in latest run. | Not tested in latest run. | NOT TESTED |
| `/entry` | Vehicle entry | `/alpr`, `/parking/entry`, `/reservations/check-in` | Blacklist-denial behavior covered by isolated API tests; no live entry submitted. | Not tested in latest run. | PARTIAL |
| `/exit` | Vehicle exit | `/parking/exit`, `/payments` | Not tested in latest run. | Not tested in latest run. | NOT TESTED |
| `/vehicles` | Vehicle management | `/vehicles` | Blacklisted registration denial covered by isolated API test; no live CRUD tested. | Not tested in latest run. | PARTIAL |
| `/slots` | Parking slots | `/slots` | Not tested in latest run. | Not tested in latest run. | NOT TESTED |
| `/reservations` | Reservations | `/reservations` | Blacklisted reservation and late-blacklist check-in denials covered by isolated API tests; no live reservation created. | Not tested in latest run. | PARTIAL |
| `/notifications` | Notifications | `/notifications` | Not tested in latest run. | Not tested in latest run. | NOT TESTED |
| `/sensors` | Sensor simulator | `/sensors`, `/slots` | Not tested in latest run. | Not tested in latest run. | NOT TESTED |
| `/payments` | Payments and receipts | `/payments/due`, `/payments/config`, `/payments/personal-wallet/*` | Live pending rows and wallet configuration loaded; receiver displayed. Review dialog opened and cancelled. No transfer or review decision was submitted. | Browser checked at 375px configured width; no horizontal overflow. | PARTIAL |
| `/payment-result` | Payment result | `/payments` | Not tested in latest run. | Not tested in latest run. | NOT TESTED |
| `/audit` | Audit log | `/audit` | Blacklist-attempt audit records verified in isolated tests; live audit page not tested. | Not tested in latest run. | PARTIAL |
| `/history` | Parking history | `/parking/history`, `/reports` | Existing report/PDF tests cover backend history output, not this live page. | Not tested in latest run. | PARTIAL |
| `/blacklist` | Blacklist management | `/blacklist` | Lifecycle and enforcement covered by isolated API tests; no live blacklist mutation performed. | Not tested in latest run. | PARTIAL |
| `/cameras` | Camera management | `/cameras` | Not tested in latest run. | Not tested in latest run. | NOT TESTED |
| `/monitor` | Live monitoring | `/cameras`, `/alpr` | Not tested in latest run; physical cameras were not tested. | Not tested in latest run. | NOT TESTED |
| `/reports` | Reports | `/reports` | Existing filtered-history/PDF backend test evidence is documented separately; this page was not loaded. | Not tested in latest run. | PARTIAL |
| `/settings` | Settings and pricing | `/settings`, `/auth` | Not tested in latest run. | Not tested in latest run. | NOT TESTED |

This is not a declaration that all route/API integrations are complete. Theme
coverage, role-by-role permissions, CRUD/filter/pagination interactions, and
mobile/tablet/desktop behavior still need route-specific real-browser checks.
See [final system verification](./FINAL_SYSTEM_VERIFICATION.md) for the
release decision and hardware/external-service limitations.
