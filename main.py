import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, InputFile
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler, ChatMemberHandler
import pytz
from datetime import time

from bot_avances import get_avances_handlers, ver_foto_avance
from avances.avances_management import get_avances_management_handler
from avances.avances_registro import get_avances_registro_handler
from avances.avances_visualization import get_avances_visualization_handler
from almacen.bot_herramientas_incidencias import get_tool_incidencia_handler
from bot_informes import get_informes_conversation_handler
from bot_comentarios import get_comentario_conversation_handler
from rrhh.bot_rrhh import get_rrhh_conversation_handlers
from almacen.bot_pedidos import get_pedidos_approval_handler, get_pedidos_preparation_handler, get_solicitar_material_handler
from almacen.bot_almacen import get_almacen_conversation_handler, view_full_inventory, listar_material_en_obra
from almacen.bot_averias import get_averias_conversation_handler  # <-- IMPORTACIÓN CORREGIDA Y AÑADIDA
import db_adapter as db
from bot_navigation import start, exit_bot
from prevencion.bot_prevencion import (
    get_prevencion_handlers,
    menu_ver_incidencias_prevencion,
    listar_incidencias_prevencion,
    cerrar_incidencia_prevencion
)
from ordenes.bot_ordenes import get_ordenes_handlers, ver_foto_orden
from usuarios.bot_usuarios import get_user_management_handlers, notify_admin_of_new_user
from ubicaciones.bot_ubicaciones import get_ubicaciones_handler
from bot_registro_personal import get_registro_personal_handler
from admin_management import admin_management_handler
from reporter import GROUP_CHAT_ID

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "7808980898:AAETMIUhwaarOWpx7KHFyN1cG3kJ7agivgs")

# =========================================================================
# MANEJADORES DE FOTOS
# =========================================================================
async def ver_foto_incidencia(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    try:
        incidencia_id = int(query.data.split('_')[3])
        foto_path = db.get_foto_path_by_incidencia_id(incidencia_id)
        if foto_path and os.path.exists(foto_path):
            with open(foto_path, 'rb') as photo_file:
                await context.bot.send_photo(chat_id=query.from_user.id, photo=InputFile(photo_file))
        else:
            await query.message.reply_text("No se encontró la foto para esta incidencia.")
    except (IndexError, ValueError):
        await query.message.reply_text("Error: ID de incidencia no válido.")
    except Exception as e:
        await query.message.reply_text(f"No se pudo enviar la foto: {e}")

async def ver_foto_prevencion(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Manejador para mostrar la foto de una incidencia de prevención."""
    query = update.callback_query
    await query.answer()
    try:
        incidencia_id = int(query.data.split('_')[2])
        details = db.get_prevencion_incidencia_details(incidencia_id)
        if details and details['foto_path'] and os.path.exists(details['foto_path']):
            with open(details['foto_path'], 'rb') as photo_file:
                await context.bot.send_photo(chat_id=query.from_user.id, photo=InputFile(photo_file))
        else:
            await query.message.reply_text("No se encontró la foto para esta incidencia.")
    except (IndexError, ValueError) as e:
        await query.message.reply_text(f"Error al procesar la solicitud: {e}")

# =========================================================================
# FUNCIÓN PRINCIPAL DEL BOT
# =========================================================================

async def handle_new_chat_members(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Se activa cuando un nuevo miembro se une a un grupo. Comprueba si está registrado.
    """
    new_members = update.chat_member.new_chat_members
    for member in new_members:
        if member.is_bot:
            continue  # Ignora a otros bots

        user_role = db.get_user_role(member.id)
        if not user_role:
            # Si el usuario no tiene rol, notifica a los administradores
            await notify_admin_of_new_user(context, member)

async def daily_reminder_callback(context: ContextTypes.DEFAULT_TYPE):
    """
    Función que se ejecuta en cada recordatorio.
    Comprueba si el registro ya se hizo y envía un aviso si no.
    """
    if not db.check_personal_registro_today():
        print(f"INFO: Ejecutando recordatorio. El registro de hoy no está hecho.")
        keyboard = [[InlineKeyboardButton("📝 Registrar Personal de Hoy", callback_data="registro_personal_start")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.send_message(
            chat_id=GROUP_CHAT_ID,
            text="⏰ *Recordatorio:* El registro diario de personal aún está pendiente.",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    else:
        print(f"INFO: Ejecutando recordatorio. El registro de hoy ya fue completado. No se envía aviso.")

def main() -> None:
    """Inicia el bot y configura todos los manejadores."""
    os.makedirs('avances_fotos', exist_ok=True)
    os.makedirs('averias_fotos', exist_ok=True)
    os.makedirs('incidencias_fotos', exist_ok=True)

    application = Application.builder().token(BOT_TOKEN).build()

    # --- REGISTRO DE HANDLERS DE CONVERSACIÓN ---
    
    # Handlers de avances (originales - mantener compatibilidad)
    for handler in get_avances_handlers():
        application.add_handler(handler)
    
    # Nuevos handlers de avances mejorados
    application.add_handler(get_avances_management_handler())
    application.add_handler(get_avances_registro_handler())
    application.add_handler(get_avances_visualization_handler())
    
    application.add_handler(get_tool_incidencia_handler())
    application.add_handler(get_informes_conversation_handler())
    application.add_handler(get_comentario_conversation_handler())
    application.add_handler(get_almacen_conversation_handler())
    application.add_handler(get_solicitar_material_handler())

    application.add_handler(get_pedidos_approval_handler())
    application.add_handler(get_pedidos_preparation_handler())
    
    # Se añaden los handlers de averías (ahora la importación es correcta)
    averias_report_handler, averias_manage_handler = get_averias_conversation_handler()
    application.add_handler(averias_report_handler)
    application.add_handler(averias_manage_handler)
    
    for handler in get_rrhh_conversation_handlers():
        application.add_handler(handler)

    for handler in get_prevencion_handlers():
        application.add_handler(handler)
    
    for handler in get_user_management_handlers():
        application.add_handler(handler)
    
    # Handler de administración de base de datos
    application.add_handler(admin_management_handler)

    # --- REGISTRO DE HANDLERS GLOBALES (COMANDOS Y BOTONES) ---
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(start, pattern='^back_to_main_menu$'))
    application.add_handler(CallbackQueryHandler(exit_bot, pattern='^exit_bot$'))
    
    application.add_handler(CallbackQueryHandler(ver_foto_avance, pattern='^ver_foto_avance_'))
    application.add_handler(CallbackQueryHandler(ver_foto_incidencia, pattern='^ver_foto_incidencia_'))
    application.add_handler(CallbackQueryHandler(menu_ver_incidencias_prevencion, pattern='^prevencion_ver_incidencias$'))
    application.add_handler(CallbackQueryHandler(listar_incidencias_prevencion, pattern='^prev_view_'))
    application.add_handler(CallbackQueryHandler(cerrar_incidencia_prevencion, pattern='^prev_close_'))
    application.add_handler(CallbackQueryHandler(ver_foto_prevencion, pattern='^prev_photo_'))
    
    # Este handler es para el botón "Ver Inventario Completo" del rol 'Almacen'
    # que muestra la lista no interactiva. El flujo interactivo se inicia desde
    # el handler de conversación de almacén.
    application.add_handler(CallbackQueryHandler(view_full_inventory, pattern='^almacen_ver_inventario$'))
    application.add_handler(CallbackQueryHandler(listar_material_en_obra, pattern='^almacen_listar_obra$'))
    application.add_handler(ChatMemberHandler(handle_new_chat_members, ChatMemberHandler.CHAT_MEMBER))
    application.add_handler(get_registro_personal_handler())
    application.add_handler(get_ubicaciones_handler())
    
    for handler in get_ordenes_handlers():
        application.add_handler(handler)
    application.add_handler(CallbackQueryHandler(ver_foto_orden, pattern='^ver_foto_orden_'))

    job_queue = application.job_queue
    spain_tz = pytz.timezone('Europe/Madrid')
    
    reminder_times = [
        time(8, 30, tzinfo=spain_tz),
        time(9, 0, tzinfo=spain_tz),
        time(9, 30, tzinfo=spain_tz),
        time(10, 0, tzinfo=spain_tz),
        time(11, 0, tzinfo=spain_tz)
    ]
    
    for i, reminder_time in enumerate(reminder_times):
        job_queue.run_daily(
            callback=daily_reminder_callback,
            time=reminder_time,
            days=(0, 1, 2, 3, 4), # Lunes a Viernes
            name=f"daily_reminder_{i}"
        )

    print("Bot iniciado. Presiona Ctrl+C para detenerlo.")
    application.run_polling()

if __name__ == "__main__":
    main()