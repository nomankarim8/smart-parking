# Final system verification

## Verified in this workspace

- Backend regression suite: **49 passed, 2 skipped**. The skips are opt-in
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
