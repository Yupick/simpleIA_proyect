"""
Sistema de recordatorios para citas y tareas.
Scheduler que verifica periódicamente y envía notificaciones.
"""
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict
from pathlib import Path
import sys

# Agregar el directorio raíz al path
BASE_DIR = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.db.personal import list_appointments, list_tasks, init_personal_db
from app.db.sqlite import list_users_with_roles, init_user_db

logger = logging.getLogger(__name__)


class ReminderScheduler:
    """Scheduler para enviar recordatorios de citas y tareas."""
    
    def __init__(self, check_interval_minutes: int = 5):
        """
        Inicializa el scheduler.
        
        Args:
            check_interval_minutes: Intervalo de verificación en minutos
        """
        self.check_interval = check_interval_minutes * 60  # Convertir a segundos
        self.running = False
        self.sent_reminders = set()  # IDs de recordatorios ya enviados
    
    async def check_appointment_reminders(self):
        """Verifica y envía recordatorios de citas próximas."""
        try:
            # Obtener todos los usuarios
            users = list_users_with_roles()
            
            for user in users:
                user_id = user['id']
                
                # Obtener citas del próximo día
                today = datetime.now()
                tomorrow = today + timedelta(days=1)
                
                appointments = list_appointments(
                    user_id=user_id,
                    start_date=today.strftime("%Y-%m-%d %H:%M:%S"),
                    end_date=tomorrow.strftime("%Y-%m-%d %H:%M:%S"),
                    status="scheduled"
                )
                
                for apt in appointments:
                    # Calcular si hay que enviar recordatorio
                    try:
                        start_time = datetime.strptime(apt['start_datetime'], "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        try:
                            start_time = datetime.strptime(apt['start_datetime'], "%Y-%m-%d %H:%M")
                        except ValueError:
                            continue
                    
                    reminder_time = start_time - timedelta(minutes=apt['reminder_minutes'])
                    
                    # Verificar si es momento de enviar el recordatorio
                    now = datetime.now()
                    reminder_key = f"apt_{apt['id']}"
                    
                    if (now >= reminder_time and 
                        now < start_time and 
                        reminder_key not in self.sent_reminders):
                        
                        # Enviar recordatorio
                        await self.send_reminder(
                            user_id=user_id,
                            reminder_type='appointment',
                            title=apt['title'],
                            details=f"Cita programada para {apt['start_datetime']}",
                            location=apt.get('location')
                        )
                        
                        # Marcar como enviado
                        self.sent_reminders.add(reminder_key)
                        logger.info(f"Sent appointment reminder for user {user_id}: {apt['title']}")
        
        except Exception as e:
            logger.error(f"Error checking appointment reminders: {e}")
    
    async def check_task_reminders(self):
        """Verifica y envía recordatorios de tareas próximas a vencer."""
        try:
            users = list_users_with_roles()
            
            for user in users:
                user_id = user['id']
                
                # Obtener tareas pendientes
                tasks = list_tasks(
                    user_id=user_id,
                    status="pending"
                )
                
                for task in tasks:
                    if not task.get('due_date'):
                        continue
                    
                    # Calcular si hay que enviar recordatorio
                    try:
                        due_date = datetime.strptime(task['due_date'], "%Y-%m-%d")
                    except ValueError:
                        continue
                    
                    # Recordatorio basado en due_date (asumiendo fin del día)
                    due_datetime = due_date.replace(hour=23, minute=59)
                    reminder_time = due_datetime - timedelta(minutes=task.get('reminder_minutes', 60))
                    
                    now = datetime.now()
                    reminder_key = f"task_{task['id']}"
                    
                    if (now >= reminder_time and 
                        now < due_datetime and 
                        reminder_key not in self.sent_reminders):
                        
                        # Enviar recordatorio
                        priority_emoji = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(task.get('priority', 'medium'), "⚪")
                        
                        await self.send_reminder(
                            user_id=user_id,
                            reminder_type='task',
                            title=f"{priority_emoji} {task['title']}",
                            details=f"Tarea vence el {task['due_date']}",
                            priority=task.get('priority', 'medium')
                        )
                        
                        self.sent_reminders.add(reminder_key)
                        logger.info(f"Sent task reminder for user {user_id}: {task['title']}")
        
        except Exception as e:
            logger.error(f"Error checking task reminders: {e}")
    
    async def send_reminder(
        self,
        user_id: int,
        reminder_type: str,
        title: str,
        details: str,
        **kwargs
    ):
        """
        Envía un recordatorio al usuario.
        
        Args:
            user_id: ID del usuario
            reminder_type: Tipo de recordatorio ('appointment' o 'task')
            title: Título del recordatorio
            details: Detalles adicionales
            **kwargs: Parámetros adicionales (location, priority, etc.)
        """
        # TODO: Implementar envío real por WhatsApp
        # Por ahora solo log
        
        message = f"🔔 Recordatorio: {title}\n{details}"
        
        if kwargs.get('location'):
            message += f"\n📍 Ubicación: {kwargs['location']}"
        
        logger.info(f"REMINDER for user {user_id}: {message}")
        
        # Aquí se integraría con el router de WhatsApp:
        # from app.api.routers.whatsapp import send_whatsapp_message
        # await send_whatsapp_message(phone_number=user_phone, message=message)
    
    async def run(self):
        """Ejecuta el scheduler en loop continuo."""
        self.running = True
        logger.info(f"Reminder scheduler started (checking every {self.check_interval}s)")
        
        while self.running:
            try:
                await self.check_appointment_reminders()
                await self.check_task_reminders()
                
                # Limpiar recordatorios antiguos (más de 1 día)
                # Para evitar que el set crezca indefinidamente
                if len(self.sent_reminders) > 1000:
                    self.sent_reminders.clear()
                
                await asyncio.sleep(self.check_interval)
            
            except Exception as e:
                logger.error(f"Error in reminder scheduler loop: {e}")
                await asyncio.sleep(60)  # Esperar 1 minuto en caso de error
    
    def stop(self):
        """Detiene el scheduler."""
        self.running = False
        logger.info("Reminder scheduler stopped")


async def start_reminder_service():
    """Inicia el servicio de recordatorios."""
    # Inicializar DBs
    init_user_db()
    init_personal_db()
    
    scheduler = ReminderScheduler(check_interval_minutes=5)
    await scheduler.run()


if __name__ == "__main__":
    # Ejecutar como servicio independiente
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )
    
    asyncio.run(start_reminder_service())
