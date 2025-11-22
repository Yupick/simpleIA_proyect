#!/bin/bash
#
# Script de pruebas de API del Módulo 4
#

API_URL="http://localhost:8000"
TOKEN=""
USER_ID=""

echo "==============================================="
echo "  PRUEBAS DE API - MÓDULO 4"
echo "==============================================="
echo

# Función para hacer peticiones
function api_call() {
    local method=$1
    local endpoint=$2
    local data=$3
    local headers=${4:-}
    
    if [ -n "$headers" ]; then
        curl -s -X "$method" "$API_URL$endpoint" \
            -H "Content-Type: application/json" \
            -H "$headers" \
            -d "$data"
    else
        curl -s -X "$method" "$API_URL$endpoint" \
            -H "Content-Type: application/json" \
            -d "$data"
    fi
}

# 1. Verificar salud
echo "1️⃣  Verificando salud de la API..."
health=$(curl -s "$API_URL/health")
echo "   $health"
echo

# 2. Registrar usuario
echo "2️⃣  Registrando usuario de prueba..."
register_response=$(curl -s -X POST "$API_URL/auth/register" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "username=api_test_user&password=test123")
echo "   $register_response"
echo

# 3. Login
echo "3️⃣  Haciendo login..."
login_response=$(curl -s -X POST "$API_URL/auth/login" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "username=api_test_user&password=test123")
echo "   $login_response"

# Extraer token
TOKEN=$(echo $login_response | python3 -c "import sys, json; print(json.load(sys.stdin).get('access_token', ''))" 2>/dev/null)
if [ -z "$TOKEN" ]; then
    echo "   ❌ Error: No se pudo obtener el token"
    exit 1
fi
echo "   ✅ Token obtenido"
echo

# 4. Crear productos
echo "4️⃣  Creando productos..."
product1=$(api_call POST "/api/user/products/" '{
    "name": "Laptop Dell XPS",
    "description": "Laptop de alta gama",
    "price": 1500.0,
    "sku": "LAP-DELL-001",
    "category": "Computadoras",
    "stock": 5
}' "Authorization: Bearer $TOKEN")
echo "   Producto 1: $product1"

product2=$(api_call POST "/api/user/products/" '{
    "name": "Mouse Razer",
    "description": "Mouse gaming RGB",
    "price": 80.0,
    "category": "Accesorios",
    "stock": 15
}' "Authorization: Bearer $TOKEN")
echo "   Producto 2: $product2"
echo

# 5. Listar productos
echo "5️⃣  Listando productos..."
products=$(curl -s -X GET "$API_URL/api/user/products/" \
    -H "Authorization: Bearer $TOKEN")
echo "   $products"
echo

# 6. Crear tarea
echo "6️⃣  Creando tarea..."
task=$(api_call POST "/api/user/personal/tasks" '{
    "title": "Revisar inventario",
    "description": "Verificar stock de productos",
    "priority": "high",
    "due_date": "2025-11-25"
}' "Authorization: Bearer $TOKEN")
echo "   $task"
echo

# 7. Crear cita
echo "7️⃣  Creando cita..."
appointment=$(api_call POST "/api/user/personal/appointments" '{
    "title": "Reunión con proveedor",
    "start_datetime": "2025-11-26 10:00:00",
    "location": "Oficina principal",
    "reminder_minutes": 30
}' "Authorization: Bearer $TOKEN")
echo "   $appointment"
echo

# 8. Crear conversación (chat)
echo "8️⃣  Enviando mensaje al asistente comercial..."
chat=$(api_call POST "/api/user/chat/message" '{
    "content": "¿Qué productos tienes disponibles?",
    "assistant_type": "commercial"
}' "Authorization: Bearer $TOKEN")
echo "   $chat" | python3 -m json.tool 2>/dev/null || echo "   $chat"
echo

# 9. Obtener estadísticas
echo "9️⃣  Obteniendo estadísticas del usuario..."
stats=$(curl -s -X GET "$API_URL/api/user/chat/stats" \
    -H "Authorization: Bearer $TOKEN")
echo "   $stats" | python3 -m json.tool 2>/dev/null || echo "   $stats"
echo

echo "==============================================="
echo "  ✅ PRUEBAS DE API COMPLETADAS"
echo "==============================================="
