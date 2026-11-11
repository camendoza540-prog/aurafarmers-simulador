#!/usr/bin/env bash
# Instalación para macOS / Linux
set -e
cd "$(dirname "$0")"
PY=$(command -v python3 || command -v python || true)
[ -z "$PY" ] && { echo "Instala Python 3.10 o superior"; exit 1; }
command -v npm >/dev/null || { echo "Instala Node.js LTS desde https://nodejs.org/"; exit 1; }

echo "[1/5] Entorno virtual"
[ -x backend/.venv/bin/python ] || "$PY" -m venv backend/.venv
echo "[2/5] Dependencias del backend"
backend/.venv/bin/python -m pip install --upgrade pip -q
backend/.venv/bin/python -m pip install -r backend/requirements.txt
echo "[3/5] Base de datos"
(cd backend && .venv/bin/python manage.py migrate)
echo "[4/5] Datos iniciales"
(cd backend && .venv/bin/python manage.py seed)
echo "[5/5] Dependencias del frontend"
(cd frontend && npm install)
echo
echo "Listo. Ejecuta ./run.sh · credenciales en backend/credenciales_locales.txt"
