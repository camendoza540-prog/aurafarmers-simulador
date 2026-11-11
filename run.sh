#!/usr/bin/env bash
# Ejecuta backend y frontend juntos (Ctrl+C detiene ambos)
cd "$(dirname "$0")"
[ -x backend/.venv/bin/python ] || { echo "Primero ejecuta ./setup.sh"; exit 1; }
(cd backend && .venv/bin/python manage.py runserver 8000) &
BACK=$!
trap 'kill $BACK 2>/dev/null' EXIT
if [ -n "$CODESPACE_NAME" ]; then
  echo ""
  echo "  GitHub Codespaces: abre https://${CODESPACE_NAME}-5173.${GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN:-app.github.dev}"
  echo "  (o la pestaña PORTS → puerto 5173). Contraseñas: backend/credenciales_locales.txt"
  echo ""
fi
cd frontend && npm run dev
