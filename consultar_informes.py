from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler,
)
import db_manager as db
from bot_navigation import end_and_return_to_menu
from reporter import escape # Importamos la función de escape mejorada

SELECTING_INFORME = range(1)

# --- Helpers de Teclado ---
def get_nav_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Menú Principal", callback_data="back_to_main_menu")]])

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data.clear()
    await query.edit_message_text(text="Operación cancelada.", reply_markup=get_nav_keyboard())
    return ConversationHandler.END

# --- Flujo de la Conversación ---
async def start_consulta_informes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("Ver Avances sin Incidencias", callback_data='ver_avances_sin_incidencias')],
        [InlineKeyboardButton("Ver Incidencias Pendientes", callback_data='show_Pendiente')],
        [InlineKeyboardButton("Ver Incidencias Resueltas", callback_data='show_Resuelta')],
        [InlineKeyboardButton("Ver Incidencias Escaladas", callback_data='show_Escalada')],
        [InlineKeyboardButton("⬅️ Menú Principal", callback_data='back_to_main_menu')],
    ]
    await query.edit_message_text("Selecciona el tipo de informe que deseas consultar:", reply_markup=InlineKeyboardMarkup(keyboard))
    return SELECTING_INFORME

async def show_incidencias_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    estado_seleccionado = query.data.split('_')[1]
    incidencias = db.get_incidencias_by_estado([estado_seleccionado])
    
    # CORREGIDO: Se escapan los puntos del final del mensaje
    await query.edit_message_text(f"Buscando incidencias: *{escape(estado_seleccionado)}*\\.\\.\\.", parse_mode='MarkdownV2')

    if not incidencias:
        await query.message.reply_text(f"✅ No hay incidencias con estado '{escape(estado_seleccionado)}'.", reply_markup=get_nav_keyboard())
        return ConversationHandler.END

    for incidencia in incidencias:
        fecha_reporte_str = incidencia['fecha_reporte'].strftime('%d/%m/%Y %H:%M')
        texto_incidencia = ""
        
        if incidencia['item_name']:
            texto_incidencia = (f"🛠️ *Incidencia Herramienta ID: {incidencia['incidencia_id']}*\n"
                                f"▪️ *Herramienta:* {escape(incidencia['item_name'])}\n")
        elif incidencia['avance_ubicacion']:
            texto_incidencia = (f"🚨 *Incidencia Avance ID: {incidencia['incidencia_id']}*\n"
                                f"📍 *Ubicación:* {escape(incidencia['avance_ubicacion'])}\n")
        
        texto_incidencia += (f"🗓️ *Fecha:* {escape(fecha_reporte_str)}\n"
                             f"👤 *Reportada por:* {escape(incidencia['reporter_name'])}\n"
                             f"▪️ *Descripción:* {escape(incidencia['descripcion'])}")

        if incidencia['resolutor']:
            texto_incidencia += f"\n\n✅ *Resuelta por:* @{escape(incidencia['resolutor'])}"
            if incidencia['resolucion_desc']:
                texto_incidencia += f"\n*Observaciones:* _{escape(incidencia['resolucion_desc'])}_"

        keyboard_buttons = []
        if estado_seleccionado == 'Pendiente':
            keyboard_buttons.append(InlineKeyboardButton("Resolver", callback_data=f"resolve_{incidencia['incidencia_id']}"))
        if incidencia['has_foto']:
            keyboard_buttons.append(InlineKeyboardButton("Ver Foto", callback_data=f"ver_foto_incidencia_{incidencia['incidencia_id']}"))
        
        reply_markup = InlineKeyboardMarkup([keyboard_buttons]) if keyboard_buttons else None
        await query.message.reply_text(text=texto_incidencia, reply_markup=reply_markup, parse_mode='MarkdownV2')

    await query.message.reply_text("Fin de la lista.", reply_markup=get_nav_keyboard())
    return ConversationHandler.END

def get_consulta_conversation_handler():
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(start_consulta_informes, pattern='^consultar_informes$')],
        states={
            SELECTING_INFORME: [CallbackQueryHandler(show_incidencias_list, pattern='^show_')],
        },
        fallbacks=[
            CallbackQueryHandler(cancel, pattern='^cancel_conversation$'),
            CallbackQueryHandler(end_and_return_to_menu, pattern='^back_to_main_menu$')
        ],
    )
