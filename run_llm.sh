#!/bin/bash
# run_llm.sh
#
# Script para iniciar distintos componentes del sistema LLM según el parámetro:
#   trainer:    Ejecuta el entrenador unificado (app/training/trainer.py)
#   api:        Ejecuta la API modular (app.main:app)
#   client:     Ejecuta el cliente web (app/llm_client.py)
#   line:       Ejecuta el cliente de línea de comandos (app/llm_client_line.py)
#   admin:      Ejecuta el CLI de administración (app/admin_cli.py)
#   all:        Inicia API modular y Web Client simultáneamente
# Sin parámetros: Inicia API modular y Web Client simultáneamente.

usage() {
        echo "╔════════════════════════════════════════════════════════════════╗"
        echo "║           LLM System - Control de Servicios                   ║"
        echo "╚════════════════════════════════════════════════════════════════╝"
        echo ""
        echo "Uso: $0 [comando] [opciones]"
        echo ""
        echo "Comandos disponibles:"
        echo "  trainer     - Ejecutar entrenador unificado"
        echo "  api         - Ejecutar solo la API modular (puerto 8000)"
        echo "  client      - Ejecutar solo el cliente web (puerto 8001)"
        echo "  line        - Ejecutar cliente de línea de comandos"
        echo "  admin       - Ejecutar CLI de administración"
        echo "              Subcomandos admin:"
        echo "              • feedback                    - Listar feedback almacenado"
        echo "              • reload                      - Recargar modelo según config"
        echo "              • users list                  - Listar todos los usuarios"
        echo "              • users grant-admin <user>    - Otorgar permisos de admin"
        echo "              • users revoke-admin <user>   - Revocar permisos de admin"
        echo "              • users info <user>           - Ver información de usuario"
        echo "              • users reset-password <user> - Cambiar contraseña de usuario"
        echo "  all         - Ejecutar API + Cliente Web (default)"
        echo ""
        echo "Ejemplos:"
        echo "  $0                              # Inicia API + Cliente Web"
        echo "  $0 all                          # Mismo que sin argumentos"
        echo "  $0 trainer                      # Solo entrenador"
        echo "  $0 api                          # Solo API"
        echo "  $0 admin feedback               # Ver feedback almacenado"
        echo "  $0 admin users list             # Listar usuarios con roles"
        echo "  $0 admin users grant-admin john # Hacer admin a 'john'"
        echo "  $0 admin users info maria       # Ver info de 'maria'"
        echo "  $0 admin users reset-password pedro # Cambiar contraseña de 'pedro'"
        echo ""
}

# Cargar variables de entorno si existe .env
if [ -f .env ]; then
    echo "📋 Cargando variables desde .env"
    set -a
    source .env
    set +a
fi

# Verificar que existe el entorno virtual
if [ ! -d "venv" ]; then
    echo "❌ Error: No se encuentra el entorno virtual 'venv'"
    echo "   Ejecuta primero: python3 -m venv venv && venv/bin/pip install -r requirements.txt"
    exit 1
fi

if [ "$#" -eq 0 ] || [ "$1" = "all" ]; then
    echo "🚀 Iniciando API modular y Web Client..."
    echo ""
    venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
    API_PID=$!
    venv/bin/uvicorn app.llm_client:app --host 0.0.0.0 --port 8001 --reload &
    CLIENT_PID=$!
    echo "✅ Servicios iniciados:"
    echo "   🔹 API modular: http://localhost:8000"
    echo "   🔹 Docs API:    http://localhost:8000/docs"
    echo "   🔹 Web Client:  http://localhost:8001"
    echo "   🔹 Admin Panel: http://localhost:8001/admin"
    echo ""
    echo "💡 Presiona Ctrl+C para detener los servicios"
    echo ""
    wait $API_PID $CLIENT_PID
else
    case "$1" in
        trainer)
            echo "🎓 Iniciando Trainer Unificado..."
            echo ""
            venv/bin/python app/training/trainer.py
            ;;
        api)
            echo "🔌 Iniciando API modular..."
            echo "   📍 http://localhost:8000"
            echo "   📚 Docs: http://localhost:8000/docs"
            echo ""
            venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
            ;;
        client)
            echo "🌐 Iniciando LLM Web Client..."
            echo "   📍 http://localhost:8001"
            echo "   ⚠️  Nota: Requiere que la API esté corriendo en puerto 8000"
            echo ""
            venv/bin/uvicorn app.llm_client:app --host 0.0.0.0 --port 8001 --reload
            ;;
        line)
            echo "💻 Iniciando LLM Client Line..."
            echo ""
            venv/bin/python app/llm_client_line.py
            ;;
        admin)
            echo "⚙️  Iniciando Admin CLI..."
            echo ""
            if [ "$#" -lt 2 ]; then
                echo "Comandos disponibles:"
                echo "  feedback                    - Listar feedback almacenado"
                echo "  reload                      - Recargar modelo según config"
                echo "  users list                  - Listar todos los usuarios con roles"
                echo "  users grant-admin <user>    - Otorgar permisos de administrador"
                echo "  users revoke-admin <user>   - Revocar permisos de administrador"
                echo "  users info <user>           - Ver información de usuario"
                echo "  users reset-password <user> - Cambiar contraseña de usuario"
                echo ""
                echo "Ejemplos:"
                echo "  $0 admin feedback"
                echo "  $0 admin users list"
                echo "  $0 admin users grant-admin john"
                echo "  $0 admin users revoke-admin maria"
                echo "  $0 admin users info pedro"
                echo "  $0 admin users reset-password ana"
                echo ""
                exit 1
            fi
            # Pasar todos los argumentos restantes al admin_cli
            shift  # Remover 'admin' del array de argumentos
            venv/bin/python -m app.admin_cli "$@"
            ;;
        help|--help|-h)
            usage
            ;;
        *)
            echo "❌ Error: Comando desconocido '$1'"
            echo ""
            usage
            exit 1
            ;;
    esac
fi
