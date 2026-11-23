
@echo off
cd /d "%~dp0"

set "GDAS_DB_PATH=%~dp0backend\data\gdas.sqlite3"

REM Preserve stored accounts and applications. Initialize only if needed.
python -m backend.prepare_data
if errorlevel 1 (
    echo Database setup failed. Existing records were not intentionally reset.
    pause
    exit /b 1
)

set "GDAS_SMTP_HOST=127.0.0.1"
set "GDAS_SMTP_PORT=1025"
set "GDAS_SMTP_FROM=gdas-notifications@arizona.edu"
set "GDAS_SMTP_STARTTLS=0"
set "GDAS_BASE_URL=http://127.0.0.1:8000"

python -m uvicorn main:app --reload

pause
