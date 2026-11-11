@echo off
cd /d "%~dp0"
if not exist "backend\.venv\Scripts\python.exe" (
  echo Primero ejecuta setup.bat
  pause & exit /b 1
)
start "Aura Farmers - Backend (Django :8000)" cmd /k "cd /d "%~dp0backend" && .venv\Scripts\python.exe manage.py runserver 8000"
start "Aura Farmers - Frontend (Vite :5173)" cmd /k "cd /d "%~dp0frontend" && npm run dev"
echo Se abrieron dos ventanas: backend y frontend.
echo El navegador se abrira en http://localhost:5173
timeout /t 4 >nul
