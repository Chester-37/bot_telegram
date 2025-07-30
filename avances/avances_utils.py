# avances/avances_utils.py
# Utilidades compartidas para el módulo de avances

import db_adapter as db_manager
from datetime import datetime, date
import pytz
from telegram.helpers import escape_markdown
import re

def escape(text):
    """Escapa texto para MarkdownV2."""
    if text is None:
        return ""
    # Caracteres especiales que necesitan escape en MarkdownV2
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    escaped_text = str(text)
    for char in special_chars:
        escaped_text = escaped_text.replace(char, f'\\{char}')
    return escaped_text

def format_user(user):
    """Formatea información del usuario para reportes."""
    if user.username:
        return f"@{user.username} \\({escape(user.first_name)}\\)"
    return escape(user.first_name)

def format_date(fecha):
    """Formatea fecha para mostrar."""
    if isinstance(fecha, str):
        try:
            fecha = datetime.strptime(fecha, '%Y-%m-%d').date()
        except ValueError:
            return escape(str(fecha))
    
    if isinstance(fecha, (datetime, date)):
        return fecha.strftime('%d/%m/%Y')
    
    return escape(str(fecha))

def format_datetime(fecha_hora):
    """Formatea fecha y hora para mostrar."""
    if isinstance(fecha_hora, str):
        try:
            fecha_hora = datetime.fromisoformat(fecha_hora.replace('Z', '+00:00'))
        except ValueError:
            return escape(str(fecha_hora))
    
    if isinstance(fecha_hora, datetime):
        return fecha_hora.strftime('%d/%m/%Y %H:%M')
    
    return escape(str(fecha_hora))

def build_ubicacion_string(ubicacion_data):
    """Construye string de ubicación jerárquica."""
    partes = []
    orden_jerarquia = ['edificio', 'zona', 'planta', 'trabajo', 'elemento']
    
    for nivel in orden_jerarquia:
        if ubicacion_data.get(nivel):
            partes.append(ubicacion_data[nivel])
    
    return " / ".join(partes) if partes else "Sin ubicación"

def parse_ubicacion_string(ubicacion_str):
    """Parsea string de ubicación en componentes."""
    if not ubicacion_str:
        return {}
    
    partes = [parte.strip() for parte in ubicacion_str.split('/')]
    orden_jerarquia = ['edificio', 'zona', 'planta', 'trabajo', 'elemento']
    
    ubicacion_data = {}
    for i, parte in enumerate(partes):
        if i < len(orden_jerarquia):
            ubicacion_data[orden_jerarquia[i]] = parte
    
    return ubicacion_data

def validate_ubicacion_hierarchy(ubicacion_data):
    """Valida que la jerarquía de ubicación sea coherente."""
    required_order = ['edificio', 'zona', 'planta']
    
    for i, nivel in enumerate(required_order):
        if not ubicacion_data.get(nivel):
            # Si falta un nivel requerido, verificar que no haya niveles posteriores
            for j in range(i + 1, len(required_order)):
                if ubicacion_data.get(required_order[j]):
                    return False, f"No se puede especificar {required_order[j]} sin {nivel}"
            break
    
    return True, "Jerarquía válida"

def format_avance_summary(avance_data):
    """Formatea resumen de avance para confirmación."""
    ubicacion = build_ubicacion_string(avance_data.get('ubicacion', {}))
    
    summary = f"*📋 Resumen del Avance*\n\n"
    summary += f"📍 *Ubicación:* {escape(ubicacion)}\n"
    
    if avance_data.get('tipo_trabajo_emoji') and avance_data.get('tipo_trabajo'):
        summary += f"🔧 *Tipo:* {avance_data['tipo_trabajo_emoji']} {escape(avance_data['tipo_trabajo'])}\n"
    
    summary += f"📝 *Trabajo:* {escape(avance_data.get('trabajo', 'Sin especificar'))}\n"
    
    if avance_data.get('fecha_trabajo'):
        summary += f"📅 *Fecha:* {format_date(avance_data['fecha_trabajo'])}\n"
    
    if avance_data.get('observaciones'):
        summary += f"💭 *Observaciones:* {escape(avance_data['observaciones'])}\n"
    
    if avance_data.get('tiene_foto'):
        summary += f"📸 *Foto:* ✅ Incluida\n"
    
    if avance_data.get('tiene_incidencia'):
        summary += f"⚠️ *Incidencia:* ✅ Reportada\n"
    
    return summary

def get_jerarquia_nivel_siguiente(nivel_actual):
    """Obtiene el siguiente nivel en la jerarquía."""
    orden = ['Edificio', 'Zona', 'Planta', 'Trabajo', 'Elemento']
    try:
        current_index = orden.index(nivel_actual)
        if current_index < len(orden) - 1:
            return orden[current_index + 1]
    except ValueError:
        pass
    return None

def get_jerarquia_nivel_anterior(nivel_actual):
    """Obtiene el nivel anterior en la jerarquía."""
    orden = ['Edificio', 'Zona', 'Planta', 'Trabajo', 'Elemento']
    try:
        current_index = orden.index(nivel_actual)
        if current_index > 0:
            return orden[current_index - 1]
    except ValueError:
        pass
    return None

def clean_text_input(text):
    """Limpia entrada de texto del usuario."""
    if not text:
        return ""
    
    # Eliminar espacios extra y caracteres especiales problemáticos
    cleaned = re.sub(r'\s+', ' ', str(text).strip())
    
    # Limitar longitud
    if len(cleaned) > 500:
        cleaned = cleaned[:500] + "..."
    
    return cleaned

def validate_work_description(descripcion):
    """Valida descripción de trabajo."""
    if not descripcion or len(descripcion.strip()) < 3:
        return False, "La descripción debe tener al menos 3 caracteres"
    
    if len(descripcion) > 500:
        return False, "La descripción no puede exceder 500 caracteres"
    
    return True, "Válida"

def validate_observations(observaciones):
    """Valida observaciones."""
    if observaciones and len(observaciones) > 1000:
        return False, "Las observaciones no pueden exceder 1000 caracteres"
    
    return True, "Válidas"

def format_estados_avance():
    """Devuelve lista de estados disponibles para avances."""
    return [
        {'codigo': 'Pendiente', 'nombre': 'Pendiente', 'emoji': '⏳'},
        {'codigo': 'En Progreso', 'nombre': 'En Progreso', 'emoji': '🔄'},
        {'codigo': 'Finalizado', 'nombre': 'Finalizado', 'emoji': '✅'},
        {'codigo': 'Con Incidencia', 'nombre': 'Con Incidencia', 'emoji': '⚠️'},
        {'codigo': 'Suspendido', 'nombre': 'Suspendido', 'emoji': '⏸️'}
    ]

def get_nivel_permiso_minimo(user_role):
    """Determina el nivel mínimo requerido según el rol del usuario."""
    permisos = {
        'Encargado': 'Planta',  # Encargados deben especificar hasta planta mínimo
        'Técnico': 'Zona',     # Técnicos pueden registrar desde zona
        'Gerente': 'Edificio'  # Gerentes pueden ver desde edificio
    }
    return permisos.get(user_role, 'Planta')

def can_user_manage_avances(user_role):
    """Verifica si el usuario puede gestionar avances (configuración)."""
    return user_role in ['Técnico']

def can_user_create_avances(user_role):
    """Verifica si el usuario puede crear avances."""
    return user_role in ['Encargado', 'Técnico']

def can_user_view_all_avances(user_role):
    """Verifica si el usuario puede ver todos los avances."""
    return user_role in ['Técnico', 'Gerente']

def can_user_view_team_avances(user_role):
    """Verifica si el usuario puede ver avances del equipo."""
    return user_role in ['Encargado', 'Técnico', 'Gerente']
