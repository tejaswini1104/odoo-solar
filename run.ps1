# Starts the whole app: applies pending database changes, then runs the API (port 8000) and the web app (port 5173).
# Usage, from this folder:  .\run.ps1
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $root

python -m pip install -q -r backend/requirements.txt
python backend/apply_migrations.py
if ($LASTEXITCODE -ne 0) { Write-Host "Database update failed. Is PostgreSQL running?" -ForegroundColor Red; exit 1 }

if (-not (Test-Path "frontend/node_modules")) { Push-Location frontend; npm install; Pop-Location }

Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root'; python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000"
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$root\frontend'; npm run dev -- --host 127.0.0.1 --port 5173"

Start-Sleep -Seconds 5
Start-Process "http://127.0.0.1:5173/"
