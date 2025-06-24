#!/bin/bash
# run_llm.sh
#
# Script para iniciar distintos componentes del sistema LLM según el parámetro:
#   trainer: Ejecuta app/llm_trainer.py
#   api:     Ejecuta la API (app/llm_api.py)
#   client:  Ejecuta el cliente web (app/llm_client.py)
#   line:    Ejecuta el cliente de línea (app/llm_client_line.py)
# Sin parámetros: Inicia la API y el Cliente Web simultáneamente.

usage() {
    echo "Uso: $0 [trainer|api|client|line]"
    echo "   trainer: Ejecuta el llm_trainer.py"
    echo "   api:     Ejecuta el llm_api.py"
    echo "   client:  Ejecuta el llm_client.py"
    echo "   line:    Ejecuta el llm_client_line.py"
    echo "Sin argumentos se inician los servidores API y Web Client"
}

if [ "$#" -eq 0 ]; then
    echo "No se proporcionó ningún parámetro. Iniciando API y Web Client..."
    uvicorn app.llm_api:app --host 0.0.0.0 --port 8000 --reload &
    uvicorn app.llm_client:app --host 0.0.0.0 --port 8001 --reload &
    echo "Servicios LLM iniciados:"
    echo "  API: http://localhost:8000"
    echo "  Web Client: http://localhost:8001"
    wait
else
    case "$1" in
        trainer)
            echo "Iniciando LLM Trainer..."
            python3 app/llm_trainer.py
            ;;
        api)
            echo "Iniciando LLM API..."
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
