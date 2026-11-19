# Administrator Guide

## Daily Operations

- Use Dashboard refresh to request live statistics, slot status, and backend health.
- Add vehicles through the Add Vehicle action.
- Use dynamic category selections; database category IDs are not assumed by Entry.
- Review Parking History and export CSV only after confirming the export succeeded.

## Authorization

- `SUPER_ADMIN`, `ADMIN`, and `OPERATOR` have operational route access.
- `SUPER_ADMIN` and `ADMIN` have administrative route access.
- `VIEWER` may access routes without restricted role maps but backend permissions remain authoritative.

## Sessions

If the session expires or the token is invalid, sign in again. A 403 means the account is valid but lacks permission.
