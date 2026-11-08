
@echo off
cd /d "%~dp0"

set "GDAS_DB_PATH=%~dp0backend\data\mvp1_demo.sqlite3"

python -m backend.demo_seed

if errorlevel 1 (
    echo Failed to load demo data.
    pause
    exit /b 1
)

set "GDAS_SMTP_HOST=127.0.0.1"
set "GDAS_SMTP_PORT=1025"
set "GDAS_SMTP_FROM=ua-gdas-demo@arizona.edu"
set "GDAS_SMTP_STARTTLS=0"
set "GDAS_BASE_URL=http://127.0.0.1:8000"

python -m uvicorn main:app --reload

pause
