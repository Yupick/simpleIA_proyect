"""
Clase base para asistentes contextuales con acceso a datos del usuario.
"""
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod


class BaseAssistant(ABC):
    """Clase base para todos los asistentes."""
    
    def __init__(self, user_id: int):
        """
        Inicializa el asistente para un usuario específico.
        
        Args:
            user_id: ID del usuario al que pertenece este asistente
        """
        self.user_id = user_id
    
    @abstractmethod
    async def process_message(self, message: str, conversation_history: List[Dict] = None) -> str:
        """
        Procesa un mensaje del usuario y genera una respuesta.
        
        Args:
            message: Mensaje del usuario
            conversation_history: Historial de conversación previo
            
        Returns:
            Respuesta generada por el asistente
        """
        pass
    
    @abstractmethod
    def get_context(self) -> Dict[str, Any]:
        """
        Obtiene el contexto relevante del usuario para el asistente.
        
        Returns:
            Diccionario con información contextual
        """
        pass
    
    def build_system_prompt(self) -> str:
        """
        Construye el prompt del sistema para el LLM.
        
        Returns:
            Prompt del sistema
        """
        return "Eres un asistente útil."
