#!/bin/bash

#echo "Navegando al directorio raíz del proyecto..."
#SCRIPT_DIR=$(dirname "$0")
#cd "$SCRIPT_DIR/.." || { echo "No se pudo cambiar al directorio raíz."; exit 1; }

echo "Verificando la disponibilidad de python3..."
if ! command -v python3 &> /dev/null; then
    echo "python3 no está instalado. Por favor, instálalo e inténtalo de nuevo."
    exit 1
fi

echo "Creando entorno virtual..."
python3 -m venv venv

echo "Activando el entorno virtual..."
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
elif [ -f "venv/Scripts/activate" ]; then
    source venv/Scripts/activate
else
    echo "No se pudo encontrar el script de activación del entorno virtual."
    exit 1
fi

echo "Actualizando pip..."
pip install --upgrade pip

# Actualizamos setuptools y wheel para evitar errores de compilación
echo "Actualizando setuptools y wheel..."
pip install --upgrade setuptools wheel

echo "Instalando dependencias desde requirements.txt..."
pip install -r requirements.txt

echo "El entorno virtual se configuró y activó correctamente."
