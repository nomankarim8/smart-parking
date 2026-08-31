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

## Frontend

Open a second terminal:

```powershell
cd smart-parking\frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

## Database

Start MySQL first, then execute `database/schema.sql` and `database/seeds.sql`.

## Demo login

Username: `admin`
Password: `Admin@12345`

Change the password before any public deployment.
