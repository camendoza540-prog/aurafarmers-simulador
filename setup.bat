@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
echo.
echo ============================================================
echo   Aura Farmers - Instalacion del simulador de inversion
echo ============================================================
echo.

rem --- Detectar Python (py launcher o python) ---
set "PY="
where py >nul 2>nul && set "PY=py -3"
if not defined PY (
  where python >nul 2>nul && set "PY=python"
)
if not defined PY (
  echo [ERROR] No se encontro Python. Instala Python 3.10 o superior desde https://www.python.org/downloads/
  echo         Marca la casilla "Add python.exe to PATH" durante la instalacion.
  pause & exit /b 1
)

where npm >nul 2>nul
if errorlevel 1 (
  echo [ERROR] No se encontro Node.js. Instala la version LTS 20.19 o superior desde https://nodejs.org/
  pause & exit /b 1
)

echo [1/5] Creando entorno virtual de Python en backend\.venv ...
if not exist "backend\.venv\Scripts\python.exe" (
  %PY% -m venv "backend\.venv" || (echo [ERROR] No se pudo crear el entorno virtual. & pause & exit /b 1)
)

echo [2/5] Instalando dependencias del backend ...
"backend\.venv\Scripts\python.exe" -m pip install --upgrade pip >nul
"backend\.venv\Scripts\python.exe" -m pip install -r "backend\requirements.txt" || (echo [ERROR] Fallo pip install. & pause & exit /b 1)

echo [3/5] Creando la base de datos ...
pushd backend
".venv\Scripts\python.exe" manage.py migrate || (popd & echo [ERROR] Fallo migrate. & pause & exit /b 1)

echo [4/5] Cargando instrumentos, historia de precios, lecciones y usuarios demo ...
".venv\Scripts\python.exe" manage.py seed || (popd & echo [ERROR] Fallo seed. & pause & exit /b 1)
popd

echo [5/5] Instalando dependencias del frontend (puede tardar unos minutos) ...
pushd frontend
call npm install || (popd & echo [ERROR] Fallo npm install. & pause & exit /b 1)
popd

echo.
echo ============================================================
echo   Listo. Ahora ejecuta run.bat (o en VS Code: Ctrl+Shift+B)
echo   Las contrasenas de las cuentas de ejemplo quedaron en
echo   backend\credenciales_locales.txt (solo en este PC).
echo ============================================================
pause
