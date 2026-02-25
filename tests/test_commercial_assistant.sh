#!/bin/bash
#
# Prueba específica del asistente comercial
#

API_URL="http://localhost:8000"

echo "==================================================="
echo "  PRUEBA DEL ASISTENTE COMERCIAL"
echo "==================================================="
echo

# 1. Login
echo "🔐 Login..."
login_response=$(curl -s -X POST "$API_URL/auth/login" \
    -H "Content-Type: application/x-www-form-urlencoded" \
    -d "username=api_test_user&password=test123")

TOKEN=$(echo $login_response | python3 -c "import sys, json; print(json.load(sys.stdin).get('access_token', ''))" 2>/dev/null)
echo "   Token obtenido"
echo

# 2. Crear más productos
echo "📦 Creando catálogo de productos..."
products=(
    '{"name": "iPhone 15 Pro", "description": "Smartphone Apple 256GB", "price": 1200.0, "category": "Smartphones", "stock": 8}'
    '{"name": "Samsung Galaxy S24", "description": "Smartphone Android flagship", "price": 1100.0, "category": "Smartphones", "stock": 12}'
    '{"name": "Teclado Mecánico Logitech", "description": "Teclado gaming RGB", "price": 150.0, "category": "Accesorios", "stock": 20}'
    '{"name": "Monitor LG UltraWide", "description": "Monitor 34 pulgadas curvo", "price": 500.0, "category": "Monitores", "stock": 6}'
    '{"name": "Auriculares Sony WH-1000XM5", "description": "Auriculares noise cancelling", "price": 350.0, "category": "Audio", "stock": 15}'
)

for product in "${products[@]}"; do
    curl -s -X POST "$API_URL/api/user/products/" \
        -H "Authorization: Bearer $TOKEN" \
        -H "Content-Type: application/json" \
        -d "$product" > /dev/null
    echo "   ✓ Producto creado"
done
echo

# 3. Preguntas al asistente
echo "💬 Conversaciones con el asistente:"
echo

queries=(
    "Hola, ¿qué laptops tienes disponibles?"
    "Necesito un smartphone de alta gama"
    "¿Tienes accesorios gaming?"
    "Busco auriculares con cancelación de ruido"
    "¿Qué monitores tienes y cuál me recomiendas?"
    "Dame información sobre el iPhone 15 Pro"
    "¿Cuál es el producto más caro que tienes?"
)

for query in "${queries[@]}"; do
    echo "❓ Usuario: $query"
    echo

    response=$(curl -s -X POST "$API_URL/api/user/chat/message" \
        -H "Authorization: Bearer $TOKEN" \
        -H "Content-Type: application/json" \
        -d "{\"content\": \"$query\", \"assistant_type\": \"commercial\"}")

    echo "🤖 Asistente:"
    echo "$response" | python3 -c "import sys, json; data=json.load(sys.stdin); print('   ' + data.get('response', 'Error').replace('\n', '\n   '))" 2>/dev/null
    echo
    echo "---"
    echo

    sleep 1
done

# 4. Estadísticas finales
echo "📊 Estadísticas del usuario:"
stats=$(curl -s -X GET "$API_URL/api/user/chat/stats" \
    -H "Authorization: Bearer $TOKEN")
echo "$stats" | python3 -m json.tool
echo

echo "==================================================="
echo "  ✅ PRUEBA COMPLETADA"
echo "==================================================="
