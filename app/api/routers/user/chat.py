"""
Router para gestión de conversaciones y chat del usuario.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List, Optional
from app.security.auth import get_current_regular_user
from app.db import conversations as conv_db
from app.assistants.commercial import CommercialAssistant
from app.assistants.personal import PersonalAssistant
from app.models import model_manager

router = APIRouter(prefix="/chat", tags=["chat"])

# Inicializar DB al importar
conv_db.init_conversations_db()


class MessageCreate(BaseModel):
    content: str
    assistant_type: str  # 'commercial' o 'personal'
    conversation_id: Optional[int] = None


class MessageResponse(BaseModel):
    role: str
    content: str
    created_at: str


@router.post("/message")
async def send_message(
    message: MessageCreate,
    current_user: dict = Depends(get_current_regular_user)
):
    """Envía un mensaje y obtiene respuesta del asistente."""
    user_id = current_user["id"]
    
    # Crear o usar conversación existente
    if message.conversation_id:
        # Verificar que la conversación pertenece al usuario
        conv = conv_db.get_conversation(message.conversation_id, user_id)
        if not conv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Conversación no encontrada"
            )
        conversation_id = message.conversation_id
    else:
        # Crear nueva conversación
        conversation_id = conv_db.create_conversation(user_id, message.assistant_type)
    
    # Guardar mensaje del usuario
    conv_db.add_message(conversation_id, "user", message.content)
    
    # Obtener historial para contexto
    history = conv_db.get_conversation_messages(conversation_id, limit=20)
    history_formatted = [
        {"role": msg["role"], "content": msg["content"]}
        for msg in history[:-1]  # Excluir el último (el que acabamos de agregar)
    ]
    
    # Enrutar al asistente apropiado
    if message.assistant_type == "commercial":
        assistant = CommercialAssistant(user_id=user_id)
    elif message.assistant_type == "personal":
        assistant = PersonalAssistant(user_id=user_id)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tipo de asistente inválido"
        )
    
    # Generar respuesta usando LLM compartido global
    response_text = await assistant.process_message(
        message=message.content,
        conversation_history=history_formatted,
        llm_provider=model_manager._provider_instance
    )
    
    # Guardar respuesta del asistente
    conv_db.add_message(conversation_id, "assistant", response_text)
    
    # Registrar evento de analytics
    conv_db.track_event(user_id, "message_sent", message.assistant_type)
    
    return {
        "conversation_id": conversation_id,
        "response": response_text
    }


@router.get("/conversations")
async def list_conversations(
    assistant_type: Optional[str] = None,
    current_user: dict = Depends(get_current_regular_user)
):
    """Lista todas las conversaciones del usuario."""
    conversations = conv_db.list_conversations(
        user_id=current_user["id"],
        assistant_type=assistant_type
    )
    return conversations


@router.get("/conversations/{conversation_id}")
async def get_conversation(
    conversation_id: int,
    current_user: dict = Depends(get_current_regular_user)
):
    """Obtiene una conversación específica con sus mensajes."""
    conversation = conv_db.get_conversation(conversation_id, current_user["id"])
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversación no encontrada"
        )
    
    messages = conv_db.get_conversation_messages(conversation_id)
    
    return {
        "conversation": conversation,
        "messages": messages
    }


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: int,
    current_user: dict = Depends(get_current_regular_user)
):
    """Elimina una conversación y sus mensajes."""
    success = conv_db.delete_conversation(conversation_id, current_user["id"])
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversación no encontrada"
        )
    return None


@router.get("/stats")
async def get_stats(current_user: dict = Depends(get_current_regular_user)):
    """Obtiene estadísticas de uso del usuario."""
    stats = conv_db.get_user_stats(current_user["id"])
    return stats


@router.get("/activity")
async def get_activity(
    days: int = 7,
    current_user: dict = Depends(get_current_regular_user)
):
    """Obtiene la actividad reciente del usuario."""
    activity = conv_db.get_recent_activity(current_user["id"], days)
    return activity
