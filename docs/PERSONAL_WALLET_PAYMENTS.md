# Personal-wallet payment submissions

This workflow supports customer transfers to configured bKash or Nagad personal
wallet numbers. It does not initiate transfers or verify transactions through a
provider API. A submitted transaction remains pending until an administrator
checks the receiving wallet history and records a verification decision.

## Configuration and database

Set `BKASH_PERSONAL_NUMBER` and/or `NAGAD_PERSONAL_NUMBER` in the backend
environment. Leave an unset receiver blank; its payment option will remain
disabled. Never place wallet PINs, passwords, or OTPs in application settings.

The backend startup `create_all` creates `wallet_payment_submissions` on
existing databases. For manually managed MySQL/MariaDB deployments, use
`database/migrations/003_personal_wallet_submissions_mysql.sql` after taking a
database backup. The same table is included in `database/schema.sql` for fresh
installations.

## Review process

The submitter provides the transaction ID, amount, and optionally a masked
payer-wallet number. The API checks the submitted amount against the server-side
amount due, rejects duplicate transaction IDs and duplicate pending claims for
the same payment, and leaves the parking slot occupied.

An `ADMIN` or `SUPER_ADMIN` must compare the submitted transaction ID and amount
against the receiving wallet history and enter a note. Approval marks the
payment paid and completes the parking session; rejection leaves the amount due
and the slot occupied. Review actions are recorded in the existing activity
log.
