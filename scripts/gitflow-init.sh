#!/usr/bin/env bash
set -euo pipefail

# Script seguro para inicializar ramas Gitflow básicas: create develop from main/master
# Uso: `bash scripts/gitflow-init.sh [origin]`

ORIGIN=${1:-origin}

die(){ echo "ERROR: $*" >&2; exit 1; }

if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  die "No estamos en un repositorio git. Ejecuta desde la raíz del repo."
fi

# Detectar rama principal existente
if git show-ref --verify --quiet refs/heads/main; then
  MAIN_BRANCH=main
elif git show-ref --verify --quiet refs/heads/master; then
  MAIN_BRANCH=master
else
  # Si no existe, usar la rama actual como principal
  MAIN_BRANCH=$(git rev-parse --abbrev-ref HEAD)
  echo "No se encontró 'main' ni 'master'. Usando '$MAIN_BRANCH' como rama principal local."
fi

echo "Rama principal detectada: $MAIN_BRANCH"

# Crear develop si no existe
if git show-ref --verify --quiet refs/heads/develop; then
  echo "La rama 'develop' ya existe localmente."
else
  echo "Creando rama 'develop' desde $MAIN_BRANCH..."
  git checkout -b develop "$MAIN_BRANCH"
  echo "Hecho: develop creada localmente."
fi

echo "Sugerencia: ahora empuja ramas al remoto y protege 'main'/'develop' en tu proveedor de Git."
echo "Comandos sugeridos:"
echo "  git push -u $ORIGIN $MAIN_BRANCH"
echo "  git push -u $ORIGIN develop"

echo "Si usas GitHub, configura branch protection rules para 'main' y 'develop' y exige PRs."
