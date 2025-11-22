"""
Sistema de acciones ejecutables para los asistentes IA.
Permite a los asistentes crear, modificar y eliminar datos mediante parsing de intenciones.
"""
import re
from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime, timedelta
from app.db import products as products_db
from app.db import personal as personal_db


class IntentParser:
    """Parser de intenciones para detectar acciones en mensajes de usuario."""
    
    # Patrones de intención para crear productos
    CREATE_PRODUCT_PATTERNS = [
        r"(crear|agregar|añadir|nuevo|añade)\s+(un\s+)?producto",
        r"quiero\s+(crear|agregar|añadir)\s+(.+?)\s+(a|al)\s+(catálogo|inventario|productos)",
        r"(agreg(a|ar)|añad(e|ir)|crea(r)?)\s+(.+?)\s+(por|a)\s+\$?(\d+)",
    ]
    
    # Patrones de intención para crear tareas
    CREATE_TASK_PATTERNS = [
        r"(crear?|agregar?|añadir?|nueva?)\s+(una\s+)?tarea",
        r"tengo\s+que\s+(.+)",
        r"debo\s+(.+)",
        r"recuérda(me)?\s+(.+)",
        r"anot(a|ar)\s+(que|una\s+tarea)?\s*:?\s*(.+)",
    ]
    
    # Patrones de intención para crear citas
    CREATE_APPOINTMENT_PATTERNS = [
        r"(crear|agregar|añadir|nueva|agendar)\s+(una\s+)?(cita|reunión|meeting|junta)",
        r"tengo\s+(una\s+)?(cita|reunión|junta)\s+(.+)",
        r"reunión\s+con\s+(.+)",
        r"(programa|agendar|anotar)\s+(una\s+)?(cita|reunión|junta)",
    ]
    
    # Patrones de fecha/hora
    DATE_PATTERNS = {
        'hoy': 0,
        'mañana': 1,
        'pasado mañana': 2,
        'el lunes': None,  # Calcular próximo lunes
        'el martes': None,
        'el miércoles': None,
        'el jueves': None,
        'el viernes': None,
        'el sábado': None,
        'el domingo': None,
    }
    
    TIME_PATTERN = r'(\d{1,2}):?(\d{2})?\s*(am|pm|a\.m\.|p\.m\.)?'
    
    # Patrones de prioridad
    PRIORITY_PATTERNS = {
        'urgente': 'high',
        'importante': 'high',
        'prioritario': 'high',
        'alta prioridad': 'high',
        'normal': 'medium',
        'media prioridad': 'medium',
        'baja prioridad': 'low',
        'cuando pueda': 'low',
    }
    
    @staticmethod
    def detect_intent(message: str) -> Tuple[str, Dict[str, Any]]:
        """
        Detecta la intención del mensaje y extrae parámetros.
        
        Returns:
            Tuple[intent, parameters]
            intent: 'create_product' | 'create_task' | 'create_appointment' | 'query' | 'unknown'
            parameters: Dict con los parámetros extraídos
        """
        message_lower = message.lower().strip()
        
        # Detectar intención de crear producto
        for pattern in IntentParser.CREATE_PRODUCT_PATTERNS:
            if re.search(pattern, message_lower):
                params = IntentParser._extract_product_params(message)
                if params:
                    return 'create_product', params
        
        # Detectar intención de crear tarea
        for pattern in IntentParser.CREATE_TASK_PATTERNS:
            if re.search(pattern, message_lower):
                params = IntentParser._extract_task_params(message)
                if params:
                    return 'create_task', params
        
        # Detectar intención de crear cita
        for pattern in IntentParser.CREATE_APPOINTMENT_PATTERNS:
            if re.search(pattern, message_lower):
                params = IntentParser._extract_appointment_params(message)
                if params:
                    return 'create_appointment', params
        
        # Si no es una acción, es una consulta
        return 'query', {}
    
    @staticmethod
    @staticmethod
    def _extract_product_params(message: str) -> Optional[Dict[str, Any]]:
        """Extrae parámetros para crear un producto."""
        message_lower = message.lower()
        
        # Intentar extraer nombre y precio
        # Patrón: "agregar/agrega laptop por $1500"
        match = re.search(r'(agreg(a|ar)|añad(e|ir)|crea(r)?)\s+(.+?)\s+por\s+\$?(\d+)', message_lower)
        if match:
            product_name = match.group(5).strip().title()
            price = float(match.group(6))
            return {
                'name': product_name,
                'price': price,
                'stock': 1
            }
        
        # Patrón: "crear producto: nombre - precio - stock"
        match = re.search(r'producto:?\s*(.+?)\s*-\s*\$?(\d+\.?\d*)\s*-?\s*(\d+)?', message_lower)
        if match:
            return {
                'name': match.group(1).strip().title(),
                'price': float(match.group(2)),
                'stock': int(match.group(3)) if match.group(3) else 1
            }
        
        # Extracción genérica: pedir nombre si solo dice "crear producto"
        if re.search(r'(crear|agregar|añadir)\s+(un\s+)?producto', message_lower):
            return {
                'needs_clarification': True,
                'missing': ['name', 'price']
            }
        
        return None
    
    @staticmethod
    def _extract_task_params(message: str) -> Optional[Dict[str, Any]]:
        """Extrae parámetros para crear una tarea."""
        message_lower = message.lower()
        
        # Extraer el título de la tarea
        title = None
        
        # Patrón: "tengo que [hacer algo]"
        match = re.search(r'tengo\s+que\s+(.+)', message_lower)
        if match:
            title = match.group(1).strip()
        
        # Patrón: "debo [hacer algo]"
        if not title:
            match = re.search(r'debo\s+(.+)', message_lower)
            if match:
                title = match.group(1).strip()
        
        # Patrón: "recuérdame [hacer algo]"
        if not title:
            match = re.search(r'recuérda(me)?\s+(.+)', message_lower)
            if match:
                title = match.group(2).strip()
        
        # Patrón: "crear/crea tarea: [título]" o "crear/crea tarea para [título]"
        if not title:
            match = re.search(r'(crear?|agregar?|añadir?)\s+(?:una\s+)?tarea\s+(?:para\s+)?(.+)', message_lower)
            if match:
                title = match.group(2).strip()
        
        if not title:
            return {
                'needs_clarification': True,
                'missing': ['title']
            }
        
        # Limpiar el título
        title = IntentParser._clean_task_title(title)
        
        # Extraer fecha si existe
        due_date = IntentParser._extract_date(message_lower)
        
        # Extraer prioridad
        priority = IntentParser._extract_priority(message_lower)
        
        return {
            'title': title.capitalize(),
            'due_date': due_date,
            'priority': priority,
            'status': 'pending'
        }
    
    @staticmethod
    def _extract_appointment_params(message: str) -> Optional[Dict[str, Any]]:
        """Extrae parámetros para crear una cita."""
        message_lower = message.lower()
        
        # Extraer título
        title = None
        
        # Patrón: "reunión con [persona]"
        match = re.search(r'reunión\s+con\s+(.+?)(?:\s+el|\s+a\s+las|\s+mañana|\s+hoy|$)', message_lower)
        if match:
            title = f"Reunión con {match.group(1).strip()}"
        
        # Patrón: "cita/junta con [persona/descripción]"
        if not title:
            match = re.search(r'(cita|junta)\s+con\s+(.+?)(?:\s+el|\s+a\s+las|\s+mañana|\s+hoy|$)', message_lower)
            if match:
                title = f"{match.group(1).capitalize()} con {match.group(2).strip()}"
        
        # Patrón: "agendar cita [descripción]"
        if not title:
            match = re.search(r'(crear|agendar|agregar)\s+(cita|reunión|junta):?\s*(.+?)(?:\s+el|\s+a\s+las|\s+mañana|\s+hoy|$)', message_lower)
            if match:
                title = match.group(3).strip()
        
        # Patrón: "tengo junta de [descripción]"
        if not title:
            match = re.search(r'tengo\s+(junta|reunión)\s+de\s+(.+?)(?:\s+el|\s+a\s+las|\s+mañana|\s+hoy|$)', message_lower)
            if match:
                title = f"{match.group(1).capitalize()} de {match.group(2).strip()}"
        
        if not title:
            # Genérica
            title = "Nueva cita"
        
        # Extraer fecha y hora
        date_str = IntentParser._extract_date(message_lower)
        time_str = IntentParser._extract_time(message_lower)
        
        # Combinar fecha y hora
        if date_str and time_str:
            start_datetime = f"{date_str} {time_str}:00"
        elif date_str:
            start_datetime = f"{date_str} 09:00:00"  # Hora por defecto
        else:
            # Fecha por defecto: mañana a las 9am
            tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
            start_datetime = f"{tomorrow} 09:00:00"
        
        return {
            'title': title.capitalize(),
            'start_datetime': start_datetime,
            'status': 'scheduled',
            'reminder_minutes': 15
        }
    
    @staticmethod
    def _clean_task_title(title: str) -> str:
        """Limpia el título de la tarea eliminando partes innecesarias."""
        # Eliminar referencias de fecha
        title = re.sub(r'\s+(hoy|mañana|pasado mañana|el\s+(lunes|martes|miércoles|jueves|viernes|sábado|domingo))', '', title)
        # Eliminar referencias de hora
        title = re.sub(r'\s+a\s+las\s+\d{1,2}:\d{2}', '', title)
        # Eliminar referencias de prioridad
        title = re.sub(r'\s+(urgente|importante|prioritario)', '', title)
        return title.strip()
    
    @staticmethod
    def _extract_date(message: str) -> Optional[str]:
        """Extrae la fecha del mensaje en formato YYYY-MM-DD."""
        message_lower = message.lower()
        
        # Buscar patrones relativos
        for pattern, days_offset in IntentParser.DATE_PATTERNS.items():
            if pattern in message_lower:
                if days_offset is not None:
                    target_date = datetime.now() + timedelta(days=days_offset)
                    return target_date.strftime("%Y-%m-%d")
                else:
                    # Calcular próximo día de la semana
                    day_name = pattern.replace('el ', '')
                    return IntentParser._get_next_weekday(day_name)
        
        # Buscar fecha explícita: DD/MM/YYYY o DD-MM-YYYY
        match = re.search(r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})', message)
        if match:
            day, month, year = match.groups()
            return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
        
        return None
    
    @staticmethod
    def _extract_time(message: str) -> Optional[str]:
        """Extrae la hora del mensaje en formato HH:MM."""
        match = re.search(IntentParser.TIME_PATTERN, message.lower())
        if match:
            hour = int(match.group(1))
            minute = int(match.group(2)) if match.group(2) else 0
            period = match.group(3)
            
            # Convertir a formato 24h si es necesario
            if period and 'pm' in period and hour < 12:
                hour += 12
            elif period and 'am' in period and hour == 12:
                hour = 0
            
            return f"{hour:02d}:{minute:02d}"
        
        return None
    
    @staticmethod
    def _extract_priority(message: str) -> str:
        """Extrae la prioridad del mensaje."""
        message_lower = message.lower()
        
        for pattern, priority in IntentParser.PRIORITY_PATTERNS.items():
            if pattern in message_lower:
                return priority
        
        return 'medium'  # Prioridad por defecto
    
    @staticmethod
    def _get_next_weekday(day_name: str) -> str:
        """Calcula la fecha del próximo día de la semana especificado."""
        weekdays = {
            'lunes': 0, 'martes': 1, 'miércoles': 2, 'jueves': 3,
            'viernes': 4, 'sábado': 5, 'domingo': 6
        }
        
        target_day = weekdays.get(day_name)
        if target_day is None:
            return None
        
        today = datetime.now()
        days_ahead = target_day - today.weekday()
        
        if days_ahead <= 0:  # El día ya pasó esta semana
            days_ahead += 7
        
        target_date = today + timedelta(days=days_ahead)
        return target_date.strftime("%Y-%m-%d")


class ActionExecutor:
    """Ejecutor de acciones para los asistentes."""
    
    @staticmethod
    def execute_action(user_id: int, intent: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecuta una acción basada en la intención detectada.
        
        Returns:
            Dict con el resultado de la acción:
            {
                'success': bool,
                'message': str,
                'data': Optional[Dict]
            }
        """
        if intent == 'create_product':
            return ActionExecutor._create_product(user_id, params)
        elif intent == 'create_task':
            return ActionExecutor._create_task(user_id, params)
        elif intent == 'create_appointment':
            return ActionExecutor._create_appointment(user_id, params)
        else:
            return {
                'success': False,
                'message': 'Intención no reconocida',
                'data': None
            }
    
    @staticmethod
    def _create_product(user_id: int, params: Dict[str, Any]) -> Dict[str, Any]:
        """Crea un producto en el catálogo."""
        if params.get('needs_clarification'):
            return {
                'success': False,
                'message': f"Necesito más información. Por favor proporciona: {', '.join(params['missing'])}",
                'data': None
            }
        
        try:
            product_id = products_db.create_product(
                user_id=user_id,
                name=params['name'],
                price=params['price'],
                description=params.get('description'),
                sku=params.get('sku'),
                category=params.get('category'),
                stock=params.get('stock', 1)
            )
            
            return {
                'success': True,
                'message': f"✅ Producto '{params['name']}' creado exitosamente por ${params['price']}",
                'data': {'product_id': product_id}
            }
        except Exception as e:
            return {
                'success': False,
                'message': f"Error al crear producto: {str(e)}",
                'data': None
            }
    
    @staticmethod
    def _create_task(user_id: int, params: Dict[str, Any]) -> Dict[str, Any]:
        """Crea una tarea."""
        if params.get('needs_clarification'):
            return {
                'success': False,
                'message': f"Necesito más información. Por favor proporciona: {', '.join(params['missing'])}",
                'data': None
            }
        
        try:
            task_id = personal_db.create_task(
                user_id=user_id,
                title=params['title'],
                description=params.get('description'),
                priority=params.get('priority', 'medium'),
                due_date=params.get('due_date'),
                category=params.get('category'),
                reminder_minutes=params.get('reminder_minutes', 60)
            )
            
            due_info = f" para el {params['due_date']}" if params.get('due_date') else ""
            priority_emoji = {'high': '🔴', 'medium': '🟡', 'low': '🟢'}.get(params.get('priority', 'medium'), '⚪')
            
            return {
                'success': True,
                'message': f"✅ Tarea creada: {priority_emoji} '{params['title']}'{due_info}",
                'data': {'task_id': task_id}
            }
        except Exception as e:
            return {
                'success': False,
                'message': f"Error al crear tarea: {str(e)}",
                'data': None
            }
    
    @staticmethod
    def _create_appointment(user_id: int, params: Dict[str, Any]) -> Dict[str, Any]:
        """Crea una cita."""
        try:
            appointment_id = personal_db.create_appointment(
                user_id=user_id,
                title=params['title'],
                description=params.get('description'),
                start_datetime=params['start_datetime'],
                end_datetime=params.get('end_datetime'),
                location=params.get('location'),
                attendees=params.get('attendees'),
                reminder_minutes=params.get('reminder_minutes', 15)
            )
            
            return {
                'success': True,
                'message': f"✅ Cita agendada: '{params['title']}' para el {params['start_datetime']}",
                'data': {'appointment_id': appointment_id}
            }
        except Exception as e:
            return {
                'success': False,
                'message': f"Error al crear cita: {str(e)}",
                'data': None
            }
