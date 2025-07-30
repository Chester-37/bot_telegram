# almacen/bot_averias.py (Versión Corregida)

import os
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    CommandHandler
)
from telegram.helpers import escape_markdown
import db_manager as db
from bot_navigation import end_and_return_to_menu, start
from reporter import send_report, escape, format_user

# Estados
AWAITING_MACHINE_NAME, AWAITING_BREAKDOWN_DESC, AWAITING_BREAKDOWN_PHOTO = range(3)
SELECTING_AVERIA_TYPE, LISTING_BREAKDOWNS, VIEWING_BREAKDOWN_DETAILS, AWAITING_DECISION_NOTES = range(3, 7)

def get_cancel_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancelar", callback_data="cancel_conversation")]])

def get_nav_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Menú Principal", callback_data="back_to_main_menu")]])

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query:
        await query.answer("Operación cancelada.")
    else:
        await update.message.reply_text("Operación cancelada.")
    group_chat_id = context.user_data.get('group_chat_id')
    context.user_data.clear()
    if group_chat_id:
        context.user_data['group_chat_id'] = group_chat_id
    await start(update, context)
    return ConversationHandler.END

# =============================================================================
# FLUJO 1: REPORTAR AVERÍA
# =============================================================================
async def start_report_breakdown(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data['new_breakdown'] = {}
    await query.edit_message_text("Por favor, escribe el nombre de la máquina o equipo averiado.", reply_markup=get_cancel_keyboard())
    return AWAITING_MACHINE_NAME

async def get_machine_name(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['new_breakdown']['maquina'] = update.message.text
    await update.message.reply_text("Entendido. Ahora describe brevemente la avería.", reply_markup=get_cancel_keyboard())
    return AWAITING_BREAKDOWN_DESC

async def get_breakdown_desc(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['new_breakdown']['descripcion'] = update.message.text
    keyboard = [
        [InlineKeyboardButton("Añadir Foto", callback_data='breakdown_add_photo')],
        [InlineKeyboardButton("Continuar sin Foto", callback_data='breakdown_skip_photo')],
        [InlineKeyboardButton("❌ Cancelar", callback_data="cancel_conversation")]
    ]
    await update.message.reply_text("¿Quieres añadir una foto de la avería?", reply_markup=InlineKeyboardMarkup(keyboard))
    return AWAITING_BREAKDOWN_PHOTO

async def get_breakdown_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query:
        await query.answer()
        if query.data == 'breakdown_add_photo':
            await query.edit_message_text("Por favor, envía la foto ahora.", reply_markup=get_cancel_keyboard())
            return AWAITING_BREAKDOWN_PHOTO
        else:
            context.user_data['new_breakdown']['foto_path'] = None
            await query.edit_message_text("Registrando avería sin foto...")
            await save_breakdown(update, context)
            return ConversationHandler.END
    else:
        photo_file = await update.message.photo[-1].get_file()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"averia_{update.effective_user.id}_{timestamp}.jpg"
        os.makedirs('averias_fotos', exist_ok=True)
        file_path = os.path.join('averias_fotos', file_name)
        await photo_file.download_to_drive(file_path)
        context.user_data['new_breakdown']['foto_path'] = file_path
        await update.message.reply_text("Foto recibida. Registrando avería...")
        await save_breakdown(update, context)
        return ConversationHandler.END

async def save_breakdown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    data = context.user_data['new_breakdown']
    message_source = update.callback_query.message if update.callback_query else update.message
    averia_id = db.create_averia(user.id, data['maquina'], data['descripcion'], data.get('foto_path'))
    await message_source.reply_text(f"✅ Avería registrada con ID #{averia_id}. Notificando a los técnicos...", reply_markup=get_nav_keyboard())
    report_text = (
        f"‼️ *Reporte: Nueva Avería de Maquinaria* ‼️\n\n"
        f"*ID Avería:* `{averia_id}`\n"
        f"*Reportada por:* {format_user(user)}\n"
        f"*Máquina:* {escape(data['maquina'])}\n"
        f"*Descripción:* {escape(data['descripcion'])}"
    )
    await send_report(context, report_text)
    ids_tecnicos = db.get_users_by_role('Tecnico')
    texto_notificacion = (f"‼️ *Nueva Avería Reportada por {format_user(user)}* ‼️\n\n"
                          f"🔩 *Máquina:* {escape(data['maquina'])}\n"
                          f"📝 *Descripción:* {escape(data['descripcion'])}")
    keyboard = [[InlineKeyboardButton("Gestionar Avería", callback_data='gestionar_averias')]]
    for tecnico in ids_tecnicos:
        await context.bot.send_message(chat_id=tecnico['id'], text=texto_notificacion, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='MarkdownV2')
    context.user_data.clear()

# =============================================================================
# FLUJO 2: GESTIONAR AVERÍA
# =============================================================================
async def averias_menu_tecnico(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("📋 Ver Averías Pendientes", callback_data="manage_Pendiente")],
        [InlineKeyboardButton("✅ Ver Averías Gestionadas", callback_data="manage_Resueltas")],
        [InlineKeyboardButton("⬅️ Menú Principal", callback_data="back_to_main_menu")]
    ]
    await query.edit_message_text("🛠️ *Gestión de Averías de Maquinaria*\n\nElige una opción:", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    return SELECTING_AVERIA_TYPE

async def show_breakdowns_by_type(update: Update, context: ContextTypes.DEFAULT_TYPE, list_type: str = None) -> int:
    query = update.callback_query
    tipo = list_type if list_type else query.data.split('_')[1]
    context.user_data['current_list_type'] = tipo
    if query:
        await query.answer()
    estados = ['Pendiente'] if tipo == 'Pendiente' else ['En Reparacion', 'Dada de Baja']
    texto_vacio = "✅ No hay averías pendientes." if tipo == 'Pendiente' else "✅ No hay averías gestionadas."
    texto_titulo = "Selecciona una avería para gestionar:" if tipo == 'Pendiente' else "Selecciona una avería para ver sus detalles:"
    averias = db.get_averias_by_estado(estados)
    if not averias:
        await query.edit_message_text(texto_vacio, reply_markup=get_nav_keyboard())
        return ConversationHandler.END
    keyboard = [[InlineKeyboardButton(f"ID #{a['id']}: {a['maquina']}", callback_data=f"view_averia_{a['id']}")] for a in averias]
    keyboard.append([InlineKeyboardButton("<< Volver", callback_data="back_to_averia_menu")])
    await query.edit_message_text(texto_titulo, reply_markup=InlineKeyboardMarkup(keyboard))
    return LISTING_BREAKDOWNS

async def view_breakdown_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    averia_id = int(query.data.split('_')[2])
    context.user_data['current_averia_id'] = averia_id
    details = db.get_averia_details(averia_id)
    if not details:
        await query.edit_message_text("❌ Error: No se encontró la avería.", reply_markup=get_nav_keyboard())
        return ConversationHandler.END
    texto = (f"🔩 *Detalle de Avería #{details['id']}*\n\n"
             f"▪️ *Reporta:* {escape_markdown(details['reporta_name'], 2)}\n"
             f"▪️ *Máquina:* {escape_markdown(details['maquina'], 2)}\n"
             f"▪️ *Descripción:* {escape_markdown(details['descripcion'], 2)}\n"
             f"▪️ *Fecha Reporte:* {details['fecha_reporte']}\n")
    keyboard = []
    if details['estado'] == 'Pendiente':
        texto += f"▪️ *Estado:* 🟠 Pendiente"
        keyboard.extend([
            [InlineKeyboardButton("✅ Autorizar Reparación", callback_data="decide_En Reparacion")],
            [InlineKeyboardButton("❌ Dar de Baja", callback_data="decide_Dada de Baja")],
        ])
    else:
        texto += (f"▪️ *Estado:* {'✅' if details['estado'] == 'En Reparacion' else '❌'} {escape_markdown(details['estado'], 2)}\n\n"
                  f"--- *Resolución* ---\n"
                  f"▪️ *Gestionada por:* {escape_markdown(details.get('tecnico_name', 'N/A'), 2)}\n"
                  f"▪️ *Fecha Decisión:* {details['fecha_decision']}\n"
                  f"▪️ *Notas del Técnico:* _{escape_markdown(details.get('notas_tecnico', 'Sin notas.'), 2)}_")
    if details['has_foto']:
        keyboard.append([InlineKeyboardButton("Ver Foto", callback_data=f"ver_foto_averia_{details['id']}")])
    keyboard.append([InlineKeyboardButton("<< Volver a la lista", callback_data="back_to_list")])
    await query.edit_message_text(texto, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='Markdown')
    return VIEWING_BREAKDOWN_DETAILS

async def ask_decision_notes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    decision = query.data.split('_')[1]
    context.user_data['decision'] = decision
    await query.edit_message_text(f"Decisión: *{escape_markdown(decision, 2)}*. \n\nPor favor, añade notas sobre la decisión.", parse_mode='Markdown', reply_markup=get_cancel_keyboard())
    return AWAITING_DECISION_NOTES

async def save_decision(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    notes = update.message.text
    averia_id = context.user_data['current_averia_id']
    decision = context.user_data['decision']
    tecnico = update.effective_user
    db.decide_averia(averia_id, tecnico.id, decision, notes)
    await update.message.reply_text(f"✅ Decisión guardada para la avería #{averia_id}.", reply_markup=get_nav_keyboard())
    details = db.get_averia_details(averia_id)
    if not details:
        context.user_data.clear()
        return ConversationHandler.END
    emoji = {'En Reparacion': '✅', 'Dada de Baja': '❌'}.get(decision, '🗣️')
    report_text = (
        f"{emoji} *Reporte: Decisión sobre Avería* {emoji}\n\n"
        f"*ID Avería:* `{averia_id}`\n"
        f"*Máquina:* {escape(details['maquina'])}\n"
        f"*Decisión:* *{escape(decision)}*\n"
        f"*Gestionada por:* {format_user(tecnico)}\n"
        f"*Notas:* {escape(notes)}"
    )
    await send_report(context, report_text)
    if details.get('reporta_id'):
        texto_notif = (f"🗣️ *Actualización sobre tu reporte de avería #{averia_id}* \\({escape(details['maquina'])}\\)\n\n"
                       f"El técnico {format_user(tecnico)} ha decidido: *{escape(decision)}*\\.\n\n"
                       f"📝 *Notas:* _{escape(notes)}_")
        await context.bot.send_message(chat_id=details['reporta_id'], text=texto_notif, parse_mode='MarkdownV2')
    context.user_data.clear()
    return ConversationHandler.END

async def back_to_previous_list(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    list_type = context.user_data.get('current_list_type', 'Pendiente')
    return await show_breakdowns_by_type(update, context, list_type=list_type)

# =============================================================================
# HANDLERS
# =============================================================================
def get_averias_conversation_handler():
    report_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_report_breakdown, pattern='^reportar_averia$')],
        states={
            AWAITING_MACHINE_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_machine_name)],
            AWAITING_BREAKDOWN_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_breakdown_desc)],
            AWAITING_BREAKDOWN_PHOTO: [
                CallbackQueryHandler(get_breakdown_photo, pattern='^breakdown_'),
                MessageHandler(filters.PHOTO, get_breakdown_photo)
            ],
        },
        fallbacks=[
            CallbackQueryHandler(cancel, pattern='^cancel_conversation$'),
            CallbackQueryHandler(end_and_return_to_menu, pattern='^back_to_main_menu$')
        ],
    )
    manage_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(averias_menu_tecnico, pattern='^gestionar_averias$')],
        states={
            SELECTING_AVERIA_TYPE: [CallbackQueryHandler(show_breakdowns_by_type, pattern='^manage_')],
            LISTING_BREAKDOWNS: [
                CallbackQueryHandler(view_breakdown_details, pattern='^view_averia_'),
                CallbackQueryHandler(averias_menu_tecnico, pattern='^back_to_averia_menu$')
            ],
            VIEWING_BREAKDOWN_DETAILS: [
                CallbackQueryHandler(ask_decision_notes, pattern='^decide_'),
                CallbackQueryHandler(back_to_previous_list, pattern='^back_to_list$')
            ],
            AWAITING_DECISION_NOTES: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_decision)],
        },
        fallbacks=[
            CallbackQueryHandler(cancel, pattern='^cancel_conversation$'),
            CallbackQueryHandler(end_and_return_to_menu, pattern='^back_to_main_menu$')
        ],
    )
    return report_handler, manage_handler
