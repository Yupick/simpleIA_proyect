#!/bin/bash
# run_llm.sh
#
# Script para iniciar distintos componentes del sistema LLM según el parámetro:
#   trainer: Ejecuta app/llm_trainer.py (legacy)
#   api:     Ejecuta la API modular (app.main:app)
#   legacyapi: Ejecuta la API antigua monolítica (app.llm_api:app)
#   client:  Ejecuta el cliente web (app/llm_client.py)
#   line:    Ejecuta el cliente de línea (app/llm_client_line.py)
# Sin parámetros: Inicia API modular y Web Client simultáneamente.

usage() {
        echo "Uso: $0 [trainer|api|legacyapi|client|line]"
        echo "   trainer:    Ejecuta llm_trainer.py (legacy)"
        echo "   api:        Ejecuta API modular (app.main:app)"
        echo "   legacyapi:  Ejecuta API monolítica antigua (app.llm_api:app)"
        echo "   client:     Ejecuta el llm_client.py"
        echo "   line:       Ejecuta el llm_client_line.py"
        echo "Sin argumentos: API modular + Web Client"
}

# Cargar variables de entorno si existe .env
if [ -f .env ]; then
    echo "Cargando variables desde .env"
    set -a
    source .env
    set +a
fi

if [ "$#" -eq 0 ]; then
    echo "Iniciando API modular y Web Client..."
    uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
    API_PID=$!
    uvicorn app.llm_client:app --host 0.0.0.0 --port 8001 --reload &
    CLIENT_PID=$!
    echo "Servicios iniciados:";
    echo "  API modular: http://localhost:8000";
    echo "  Web Client:  http://localhost:8001";
    wait $API_PID $CLIENT_PID
else
    case "$1" in
        trainer)
            echo "Iniciando Trainer Unificado..."
            python3 app/training/trainer.py
            ;;
        api)
            echo "Iniciando API modular..."
            uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
            ;;
        legacyapi)
            echo "Iniciando API monolítica legacy..."
            uvicorn app.llm_api:app --host 0.0.0.0 --port 8000 --reload
            ;;
        client)
            echo "Iniciando LLM Web Client..."
            uvicorn app.llm_client:app --host 0.0.0.0 --port 8001 --reload
            ;;
        line)
            echo "Iniciando LLM Client Line..."
            python3 app/llm_client_line.py
            ;;
        *)
            usage
            exit 1
            ;;
    esac
fi
