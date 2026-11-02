# Administrator account setup

Run these commands from `backend\` so the backend reads `backend\.env`:

```powershell
.\venv\Scripts\python.exe admin_account.py bootstrap
```

The command creates the first `SUPER_ADMIN` only when no `ADMIN` or
`SUPER_ADMIN` account exists. It asks for a password twice using hidden
terminal input, validates the configured minimum length and character classes,
stores only an Argon2 hash, requires password rotation at first sign-in, and
records an audit event. It will not create a second administrator.

To recover an existing administrator account, use the protected local
database configuration and run:

```powershell
.\venv\Scripts\python.exe admin_account.py reset --username admin
```

The reset command also reads the password through hidden terminal prompts; do
not put a password in a command argument or source file. Passwords must contain
at least 12 characters with upper-case, lower-case, numeric, and special
characters. Recent password reuse is rejected. Resetting increments the
password version, invalidates existing access tokens, updates the password
timestamp, and records an audit event. Add `--require-rotation` to require an
additional password change at next sign-in.

The commands do not display or log password values. They do not reactivate
disabled accounts. Start the API only after the database is available and the
administrator account is initialized. Never publish `backend\.env`.
