"""
Asistente comercial que ayuda con consultas de productos.
"""
import json
from typing import List, Dict, Any, Optional
from app.assistants.base import BaseAssistant
from app.assistants.actions import IntentParser, ActionExecutor
from app.db import products as products_db


class CommercialAssistant(BaseAssistant):
    """Asistente especializado en consultas comerciales y productos."""
    
    def __init__(self, user_id: int):
        super().__init__(user_id)
        self.products_cache = None
    
    def get_context(self) -> Dict[str, Any]:
        """Obtiene el contexto comercial del usuario (productos, categorías)."""
        if self.products_cache is None:
            self.products_cache = products_db.list_products(
                user_id=self.user_id,
                active_only=True
            )
        
        categories = products_db.get_categories(self.user_id)
        product_count = len(self.products_cache)
        
        return {
            "product_count": product_count,
            "categories": categories,
            "products": self.products_cache
        }
    
    def build_system_prompt(self) -> str:
        """Construye el prompt del sistema con información de productos."""
        context = self.get_context()
        
        # Construir resumen de productos para el contexto
        products_summary = []
        for p in context["products"][:50]:  # Limitar a 50 productos para no saturar el prompt
            products_summary.append(
                f"- {p['name']} ({p.get('category', 'Sin categoría')}): ${p['price']:.2f}"
                + (f" - Stock: {p['stock']}" if p['stock'] > 0 else " - Sin stock")
                + (f" - {p['description'][:100]}" if p.get('description') else "")
            )
        
        products_text = "\n".join(products_summary)
        
        prompt = f"""Eres un asistente comercial especializado en ayudar con consultas sobre productos.

**Información del catálogo:**
- Total de productos: {context['product_count']}
- Categorías disponibles: {', '.join(context['categories']) if context['categories'] else 'Ninguna'}

**Productos disponibles:**
{products_text if products_text else "No hay productos registrados aún."}

**Tus capacidades:**
1. Consultar precios y disponibilidad de productos
2. Recomendar productos según necesidades del cliente
3. Informar sobre categorías y stock
4. Responder preguntas sobre características de productos

**Instrucciones:**
- Sé conciso y preciso en tus respuestas
- Si no encuentras un producto específico, sugiere alternativas similares
- Siempre menciona el precio cuando se consulta un producto
- Indica claramente si un producto está sin stock
- Si el cliente pide algo que no existe, ofrece ayuda para encontrar alternativas
"""
        return prompt
    
    def search_relevant_products(self, query: str, limit: int = 5) -> List[Dict]:
        """
        Busca productos relevantes para una consulta usando búsqueda semántica.
        
        Args:
            query: Consulta de búsqueda
            limit: Número máximo de resultados
            
        Returns:
            Lista de productos relevantes
        """
        # Obtener todos los productos del usuario
        all_products = self.get_context()["products"]
        if not all_products:
            return []
        
        query_lower = query.lower()
        
        # Extraer palabras clave de la consulta (ignorar palabras comunes)
        stop_words = {'el', 'la', 'los', 'las', 'un', 'una', 'de', 'del', 'que', 'para', 'con', 'por', 'en', 
                      'qué', 'cuál', 'tienes', 'tiene', 'hay', 'busco', 'necesito', 'quiero', 'me', 'te'}
        query_words = [w for w in query_lower.split() if w not in stop_words and len(w) > 2]
        
        # Búsqueda por palabras clave
        matches = []
        for product in all_products:
            score = 0
            product_text = (
                f"{product['name']} "
                f"{product.get('description', '')} "
                f"{product.get('category', '')}"
            ).lower()
            
            # Buscar cada palabra clave
            for word in query_words:
                if word in product_text:
                    # Mayor puntaje si está en el nombre
                    if word in product['name'].lower():
                        score += 10
                    # Puntaje medio si está en la descripción
                    elif product.get('description') and word in product['description'].lower():
                        score += 5
                    # Puntaje bajo si está en la categoría
                    elif product.get('category') and word in product['category'].lower():
                        score += 3
            
            # Búsqueda exacta de frases
            if query_lower in product_text:
                score += 20
            
            # SKU exacto
            if product.get('sku') and query_lower in product['sku'].lower():
                score += 15
            
            if score > 0:
                product['_relevance_score'] = score
                matches.append(product)
        
        # Si no hay coincidencias y la consulta es genérica, devolver todos los productos
        if not matches and len(query_words) == 0:
            return all_products[:limit]
        
        # Ordenar por relevancia
        matches.sort(key=lambda x: x.get('_relevance_score', 0), reverse=True)
        return matches[:limit]
    
    async def process_message(
        self,
        message: str,
        conversation_history: List[Dict] = None,
        llm_provider = None
    ) -> str:
        """
        Procesa un mensaje del usuario y genera una respuesta.
        
        Args:
            message: Mensaje del usuario
            conversation_history: Historial de conversación
            llm_provider: Proveedor de LLM a usar (opcional)
            
        Returns:
            Respuesta del asistente
        """
        # Primero detectar si es una acción (crear producto, etc.)
        intent, params = IntentParser.detect_intent(message)
        
        if intent == 'create_product':
            # Ejecutar la acción de crear producto
            result = ActionExecutor.execute_action(self.user_id, intent, params)
            
            if result['success']:
                # Invalidar caché para reflejar el nuevo producto
                self.products_cache = None
                return result['message']
            else:
                return result['message']
        
        # Si no es una acción, proceder con consulta normal
        # Buscar productos relevantes para el mensaje
        relevant_products = self.search_relevant_products(message)
        
        # Construir contexto adicional con productos relevantes
        products_context = ""
        if relevant_products:
            products_context = "\n\n**Productos relevantes para esta consulta:**\n"
            for p in relevant_products:
                products_context += (
                    f"- **{p['name']}** (ID: {p['id']})\n"
                    f"  Precio: ${p['price']:.2f}\n"
                    f"  Categoría: {p.get('category', 'Sin categoría')}\n"
                    f"  Stock: {p['stock']}\n"
                )
                if p.get('description'):
                    products_context += f"  Descripción: {p['description']}\n"
                products_context += "\n"
        
        # Construir el prompt completo
        system_prompt = self.build_system_prompt()
        
        # Si hay un proveedor LLM, usarlo
        if llm_provider:
            messages = [
                {"role": "system", "content": system_prompt},
            ]
            
            # Agregar historial si existe
            if conversation_history:
                messages.extend(conversation_history)
            
            # Agregar mensaje actual con contexto de productos
            user_message = message
            if products_context:
                user_message += products_context
            
            messages.append({"role": "user", "content": user_message})
            
            # Generar respuesta con el LLM
            try:
                response = await llm_provider.generate(messages)
                return response
            except Exception as e:
                return f"Error al generar respuesta: {str(e)}"
        
        # Fallback sin LLM: respuesta basada en reglas simples
        if relevant_products:
            response = "Encontré estos productos que podrían interesarte:\n\n"
            for p in relevant_products:
                response += (
                    f"📦 **{p['name']}**\n"
                    f"💰 Precio: ${p['price']:.2f}\n"
                )
                if p['stock'] > 0:
                    response += f"✅ Stock disponible: {p['stock']} unidades\n"
                else:
                    response += "❌ Sin stock actualmente\n"
                
                if p.get('description'):
                    response += f"📝 {p['description']}\n"
                response += "\n"
            
            return response
        else:
            return (
                "No encontré productos que coincidan con tu consulta. "
                "¿Podrías darme más detalles sobre lo que buscas?"
            )
    
    def format_product_list(self, products: List[Dict]) -> str:
        """Formatea una lista de productos para mostrar."""
        if not products:
            return "No hay productos disponibles."
        
        result = []
        for p in products:
            result.append(
                f"• {p['name']} - ${p['price']:.2f} "
                f"({p['stock']} en stock)"
            )
        
        return "\n".join(result)
    
    def invalidate_cache(self):
        """Invalida el caché de productos (llamar después de modificaciones)."""
        self.products_cache = None
