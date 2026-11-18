@echo off
rem Starts DayCompass on this computer (database + API + site) and opens it in your browser.
rem Safe to run again: anything that is already running is left alone.
cd /d "%~dp0.."

docker compose up -d
if errorlevel 1 (
  echo.
  echo Could not start the database. Is Docker Desktop running? Start it, wait until it says "running", then try again.
  pause
  exit /b 1
)

netstat -ano | findstr ":8000 " | findstr LISTENING >nul
if errorlevel 1 (
  start "DayCompass API (close this window to stop)" /min cmd /k "cd backend && venv\Scripts\python -m uvicorn app.main:app --port 8000"
) else (
  echo API is already running.
)

netstat -ano | findstr ":5173 " | findstr LISTENING >nul
if errorlevel 1 (
  start "DayCompass site (close this window to stop)" /min cmd /k "cd frontend && npm run dev -- --port 5173 --strictPort"
) else (
  echo The site is already running.
)

echo Opening DayCompass...
timeout /t 8 /nobreak >nul
start "" http://localhost:5173
