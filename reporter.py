# reporter.py

import os
from telegram import User, InputFile
from telegram.ext import ContextTypes
from telegram.helpers import escape_markdown

# -----------------------------------------------------------------------------
# ID del grupo de Telegram donde se enviarán todos los reportes.
# -----------------------------------------------------------------------------
#GROUP_CHAT_ID = "-123456789"  # <--- Reemplaza si es necesario
GROUP_CHAT_ID = os.getenv("GROUP_CHAT_ID")
async def send_report(context: ContextTypes.DEFAULT_TYPE, text: str, photo_path: str = None):
    """
    Envía un mensaje de reporte al chat de grupo, con una foto opcional.
    """
    if not GROUP_CHAT_ID or "AQUÍ_VA_LA_ID" in str(GROUP_CHAT_ID):
        print(f"ADVERTENCIA: GROUP_CHAT_ID no está configurado en reporter.py. Reporte no enviado:\n{text}")
        return

    try:
        if photo_path and os.path.exists(photo_path):
            # Si se proporciona una ruta de foto válida, se envía la foto con el texto como pie.
            with open(photo_path, 'rb') as photo_file:
                await context.bot.send_photo(
                    chat_id=GROUP_CHAT_ID,
                    photo=InputFile(photo_file),
                    caption=text,
                    parse_mode='MarkdownV2'
                )
        else:
            # Si no hay foto, se envía solo el mensaje de texto.
            await context.bot.send_message(
                chat_id=GROUP_CHAT_ID,
                text=text,
                parse_mode='MarkdownV2'
            )
    except Exception as e:
        print(f"Error al enviar reporte al grupo {GROUP_CHAT_ID}: {e}")
        # Intento de enviar sin formato si falla el parseo
        try:
            await context.bot.send_message(
                chat_id=GROUP_CHAT_ID,
                text=f"Error de formato en reporte. Contenido:\n\n{text}"
            )
        except Exception as e2:
            print(f"Fallo el envío de emergencia al grupo {GROUP_CHAT_ID}: {e2}")

def escape(text: str) -> str:
    """
    Función de ayuda para escapar texto para MarkdownV2 usando la función oficial.
    """
    if text is None:
        return ""
    return escape_markdown(str(text), version=2)

def format_user(user: User) -> str:
    """
    Formatea la información de un usuario para los reportes,
    escapando caracteres especiales para MarkdownV2.
    """
    if not user:
        return "N/A"
    
    first_name = escape(user.first_name)
    username_part = ""
    if user.username:
        username_part = f" \\(@{escape(user.username)}\\)"
        
    return f"{first_name}{username_part}"
