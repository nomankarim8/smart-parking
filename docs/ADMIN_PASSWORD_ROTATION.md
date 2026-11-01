# Administrator password rotation

## What changes on upgrade

At startup the backend adds the password-rotation columns to an existing MySQL
or MariaDB `users` table if they are missing. That one-time migration marks
existing `ADMIN` and `SUPER_ADMIN` accounts with `must_change_password`.
Existing accounts are preserved; they are not deleted or recreated. Fresh
administrators created by bootstrap do not inherit the legacy rotation flag.

The equivalent versioned SQL is
`database/migrations/002_admin_password_rotation_mysql.sql`. Back up the
database before manual migration. Do not execute both the SQL migration and
startup migration against an already upgraded table.

## First sign-in after upgrade

An affected administrator can authenticate with their current password, but
all protected application routes are denied until the password is changed.
The only authenticated application actions available during this state are
`GET /api/v1/auth/me`, `POST /api/v1/auth/change-password`, and sign-out in
the frontend.

Choose a password with at least 12 characters, upper- and lower-case letters,
a number, and a symbol. The five most recent previous passwords cannot be
reused. The new password is hashed with Argon2; plaintext credentials are not
stored. Changing the password increments the account's password version,
revoking previously issued access tokens. The successful rotation is
timestamped and audit-logged.

If no administrator can authenticate, use the existing protected database
administration process to recover the account. Do not remove the user or
manually clear `must_change_password`.

## Configuration and verification

`PASSWORD_MIN_LENGTH` defaults to 12 and cannot be configured below 12.
Initial administrator creation still uses `INITIAL_ADMIN_PASSWORD` and does
not use a shared default. The frontend routes flagged accounts directly to
the password-change screen.

Run the isolated tests from `backend\`:

```powershell
..\venv\Scripts\python.exe -m pytest tests\test_admin_password_rotation.py -q
```
