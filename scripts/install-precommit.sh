#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

echo "Instalando dependencias de desarrollo (pre-commit, ruff, black, detect-secrets)..."
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt

echo "Instalando ganchos de pre-commit..."
pre-commit install
pre-commit install --hook-type pre-push

echo "Ejecutando pre-commit en todo el repositorio (first-run)..."
pre-commit run --all-files || true

echo "Listo. Para desinstalar: pre-commit uninstall"
