"""
Router para integración con WhatsApp Business API.
Procesa webhooks de WhatsApp y enruta mensajes a los asistentes apropiados.
"""
from fastapi import APIRouter, Request, HTTPException, status, Depends
from pydantic import BaseModel
from typing import Optional, Dict, Any
import logging
from app.assistants.commercial import CommercialAssistant
from app.assistants.personal import PersonalAssistant
from app.db.sqlite import get_user_by_id

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])
logger = logging.getLogger(__name__)


class WhatsAppMessage(BaseModel):
    """Modelo para mensajes de WhatsApp."""
    phone_number: str
    message: str
    user_id: Optional[int] = None
    context: Optional[str] = None  # 'commercial' o 'personal'


class WhatsAppResponse(BaseModel):
    """Respuesta de WhatsApp."""
    success: bool
    response: Optional[str] = None
    error: Optional[str] = None


# Mapeo de números de teléfono a user_ids (en producción usar DB)
PHONE_USER_MAPPING = {}


def detect_intent(message: str) -> str:
    """
    Detecta la intención del mensaje para enrutar al asistente correcto.
    
    Returns:
        'commercial' o 'personal'
    """
    message_lower = message.lower()
    
    # Palabras clave comerciales
    commercial_keywords = [
        'producto', 'precio', 'comprar', 'stock', 'disponible',
        'catálogo', 'cuánto cuesta', 'vender', 'inventario'
    ]
    
    # Palabras clave personales
    personal_keywords = [
        'cita', 'reunión', 'agenda', 'tarea', 'recordar',
        'calendario', 'compromiso', 'pendiente', 'hacer'
    ]
    
    # Contar coincidencias
    commercial_score = sum(1 for kw in commercial_keywords if kw in message_lower)
    personal_score = sum(1 for kw in personal_keywords if kw in message_lower)
    
    # Enrutar según score más alto
    if commercial_score > personal_score:
        return 'commercial'
    elif personal_score > commercial_score:
        return 'personal'
    else:
        # Por defecto, comercial (puede configurarse por usuario)
        return 'commercial'


@router.post("/webhook", response_model=WhatsAppResponse)
async def whatsapp_webhook(message: WhatsAppMessage):
    """
    Procesa mensajes entrantes de WhatsApp.
    
    Flow:
    1. Identifica al usuario por número de teléfono
    2. Detecta la intención (comercial/personal)
    3. Enruta al asistente apropiado
    4. Devuelve la respuesta para enviar por WhatsApp
    """
    try:
        # 1. Identificar usuario
        user_id = message.user_id
        if not user_id:
            user_id = PHONE_USER_MAPPING.get(message.phone_number)
        
        if not user_id:
            return WhatsAppResponse(
                success=False,
                error="Usuario no registrado. Contacte con soporte."
            )
        
        # Verificar que el usuario existe
        user = get_user_by_id(user_id)
        if not user:
            return WhatsAppResponse(
                success=False,
                error="Usuario no encontrado"
            )
        
        # 2. Detectar intención o usar contexto proporcionado
        intent = message.context or detect_intent(message.message)
        logger.info(f"Message from {message.phone_number} routed to {intent} assistant")
        
        # 3. Enrutar al asistente apropiado
        response_text = ""
        
        if intent == 'commercial':
            assistant = CommercialAssistant(user_id=user_id)
            response_text = await assistant.process_message(
                message=message.message,
                conversation_history=None,
                llm_provider=None  # TODO: Conectar con provider LLM
            )
        
        elif intent == 'personal':
            assistant = PersonalAssistant(user_id=user_id)
            response_text = await assistant.process_message(
                message=message.message,
                conversation_history=None,
                llm_provider=None  # TODO: Conectar con provider LLM
            )
        
        else:
            response_text = "No pude entender tu mensaje. ¿Preguntas sobre productos o sobre tu agenda?"
        
        return WhatsAppResponse(
            success=True,
            response=response_text
        )
    
    except Exception as e:
        logger.error(f"Error processing WhatsApp message: {e}")
        return WhatsAppResponse(
            success=False,
            error="Error al procesar el mensaje"
        )


@router.post("/link-phone")
async def link_phone_to_user(phone_number: str, user_id: int):
    """
    Vincula un número de teléfono con un usuario.
    En producción esto debería estar en una DB.
    """
    PHONE_USER_MAPPING[phone_number] = user_id
    return {"success": True, "message": f"Teléfono {phone_number} vinculado a user {user_id}"}


@router.get("/linked-phones")
async def get_linked_phones():
    """Obtiene todos los números vinculados (admin only)."""
    return PHONE_USER_MAPPING


@router.post("/send")
async def send_whatsapp_message(
    phone_number: str,
    message: str
):
    """
    Envía un mensaje por WhatsApp (outbound).
    TODO: Implementar integración real con WhatsApp Business API.
    """
    logger.info(f"Sending WhatsApp message to {phone_number}: {message}")
    
    # Aquí iría la integración real con WhatsApp Business API
    # Por ahora solo log
    
    return {
        "success": True,
        "message": "Mensaje enviado (simulado)",
        "phone": phone_number
    }


@router.get("/verify")
async def verify_webhook(request: Request):
    """
    Verifica el webhook de WhatsApp (requerido por WhatsApp Business API).
    
    WhatsApp enviará un GET con parámetros:
    - hub.mode=subscribe
    - hub.challenge=<random_string>
    - hub.verify_token=<your_token>
    """
    params = request.query_params
    
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")
    
    # TODO: Configurar VERIFY_TOKEN en settings
    VERIFY_TOKEN = "YOUR_WHATSAPP_VERIFY_TOKEN"
    
    if mode == "subscribe" and token == VERIFY_TOKEN:
        logger.info("WhatsApp webhook verified successfully")
        return int(challenge)
    else:
        raise HTTPException(status_code=403, detail="Verification failed")
