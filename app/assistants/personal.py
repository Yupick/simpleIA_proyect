"""
Asistente personal que ayuda con agenda, tareas y productividad.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta, date
from app.assistants.base import BaseAssistant
from app.db import personal as personal_db
from app.assistants.actions import IntentParser, ActionExecutor


class PersonalAssistant(BaseAssistant):
    """Asistente especializado en productividad personal (agenda y tareas)."""
    
    def __init__(self, user_id: int):
        super().__init__(user_id)
        self.appointments_cache = None
        self.tasks_cache = None
    
    def get_context(self) -> Dict[str, Any]:
        """Obtiene el contexto de agenda y tareas del usuario."""
        if self.appointments_cache is None:
            # Obtener citas próximas (próximos 30 días)
            today = datetime.now().strftime("%Y-%m-%d")
            future_date = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
            self.appointments_cache = personal_db.list_appointments(
                user_id=self.user_id,
                start_date=today,
                end_date=future_date,
                status="scheduled"
            )
        
        if self.tasks_cache is None:
            self.tasks_cache = personal_db.list_tasks(
                user_id=self.user_id,
                status="pending"
            )
        
        return {
            "upcoming_appointments": self.appointments_cache,
            "pending_tasks": self.tasks_cache,
            "appointments_count": len(self.appointments_cache),
            "tasks_count": len(self.tasks_cache)
        }
    
    def build_system_prompt(self) -> str:
        """Construye el prompt del sistema con información de agenda y tareas."""
        context = self.get_context()
        
        # Construir resumen de citas próximas
        appointments_summary = []
        for apt in context["upcoming_appointments"][:10]:
            appointments_summary.append(
                f"- {apt['title']} - {apt['start_datetime']}"
                + (f" en {apt['location']}" if apt.get('location') else "")
            )
        
        # Construir resumen de tareas pendientes
        tasks_summary = []
        for task in context["pending_tasks"][:15]:
            priority_icon = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(task['priority'], "⚪")
            tasks_summary.append(
                f"{priority_icon} {task['title']}"
                + (f" - Vence: {task['due_date']}" if task.get('due_date') else " - Sin fecha límite")
            )
        
        prompt = f"""Eres un asistente personal especializado en gestión de tiempo y productividad.

**Estado actual de la agenda:**
- Citas programadas: {context['appointments_count']}
- Tareas pendientes: {context['tasks_count']}

**Próximas citas:**
{chr(10).join(appointments_summary) if appointments_summary else "No hay citas programadas."}

**Tareas pendientes:**
{chr(10).join(tasks_summary) if tasks_summary else "No hay tareas pendientes."}

**Tus capacidades:**
1. Consultar agenda y recordar citas
2. Gestionar tareas (crear, actualizar estado, priorizar)
3. Sugerir organización de tiempo
4. Recordar compromisos y fechas límite
5. Ayudar con planificación de actividades

**Instrucciones:**
- Sé proactivo sugiriendo organización cuando veas muchas tareas
- Avisa si hay conflictos de horarios en las citas
- Prioriza tareas urgentes (con fecha límite cercana)
- Usa lenguaje amigable y motivador
- Ofrece ayuda para crear nuevas tareas o citas cuando el usuario mencione compromisos
"""
        return prompt
    
    def get_upcoming_appointments(self, days: int = 7) -> List[Dict]:
        """Obtiene las citas próximas en los siguientes N días."""
        today = datetime.now().strftime("%Y-%m-%d")
        future_date = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
        
        return personal_db.list_appointments(
            user_id=self.user_id,
            start_date=today,
            end_date=future_date,
            status="scheduled"
        )
    
    def get_pending_tasks_by_priority(self) -> Dict[str, List[Dict]]:
        """Obtiene las tareas pendientes agrupadas por prioridad."""
        tasks = personal_db.list_tasks(
            user_id=self.user_id,
            status="pending"
        )
        
        grouped = {"high": [], "medium": [], "low": []}
        for task in tasks:
            priority = task.get("priority", "medium")
            if priority in grouped:
                grouped[priority].append(task)
        
        return grouped
    
    def get_overdue_tasks(self) -> List[Dict]:
        """Obtiene las tareas vencidas."""
        all_tasks = personal_db.list_tasks(
            user_id=self.user_id,
            status="pending"
        )
        
        today = datetime.now().date()
        overdue = []
        
        for task in all_tasks:
            if task.get('due_date'):
                try:
                    due = datetime.strptime(task['due_date'], "%Y-%m-%d").date()
                    if due < today:
                        overdue.append(task)
                except:
                    pass
        
        return overdue
    
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
        # Primero detectar si es una acción (crear tarea, cita, etc.)
        intent, params = IntentParser.detect_intent(message)
        
        if intent in ['create_task', 'create_appointment']:
            # Ejecutar la acción correspondiente
            result = ActionExecutor.execute_action(self.user_id, intent, params)
            
            if result['success']:
                # Invalidar caché para reflejar los cambios
                self.invalidate_cache()
                return result['message']
            else:
                return result['message']
        
        # Si no es una acción, proceder con consulta normal
        # Construir contexto adicional relevante
        message_lower = message.lower()
        additional_context = ""
        
        # Si pregunta por citas
        if any(word in message_lower for word in ['cita', 'reunión', 'reuniones', 'agenda', 'calendario']):
            upcoming = self.get_upcoming_appointments(7)
            if upcoming:
                additional_context += "\n\n**Citas próximas (7 días):**\n"
                for apt in upcoming:
                    additional_context += (
                        f"- {apt['title']}\n"
                        f"  Fecha: {apt['start_datetime']}\n"
                    )
                    if apt.get('location'):
                        additional_context += f"  Lugar: {apt['location']}\n"
        
        # Si pregunta por tareas
        if any(word in message_lower for word in ['tarea', 'tareas', 'pendiente', 'hacer', 'completar']):
            tasks_by_priority = self.get_pending_tasks_by_priority()
            overdue = self.get_overdue_tasks()
            
            if overdue:
                additional_context += "\n\n**⚠️ Tareas vencidas:**\n"
                for task in overdue:
                    additional_context += f"- {task['title']} (Venció: {task['due_date']})\n"
            
            if tasks_by_priority["high"]:
                additional_context += "\n\n**🔴 Tareas de alta prioridad:**\n"
                for task in tasks_by_priority["high"]:
                    additional_context += f"- {task['title']}"
                    if task.get('due_date'):
                        additional_context += f" (Vence: {task['due_date']})"
                    additional_context += "\n"
        
        # Construir el prompt completo
        system_prompt = self.build_system_prompt()
        
        # Si hay un proveedor LLM, usarlo
        if llm_provider:
            messages = [
                {"role": "system", "content": system_prompt},
            ]
            
            if conversation_history:
                messages.extend(conversation_history)
            
            user_message = message
            if additional_context:
                user_message += additional_context
            
            messages.append({"role": "user", "content": user_message})
            
            try:
                response = await llm_provider.generate(messages)
                return response
            except Exception as e:
                return f"Error al generar respuesta: {str(e)}"
        
        # Fallback sin LLM: respuesta basada en reglas
        if additional_context:
            return additional_context
        else:
            return (
                "Estoy aquí para ayudarte con tu agenda y tareas. "
                "¿Quieres ver tus próximas citas, tareas pendientes, o crear algo nuevo?"
            )
    
    def invalidate_cache(self):
        """Invalida el caché (llamar después de modificaciones)."""
        self.appointments_cache = None
        self.tasks_cache = None
