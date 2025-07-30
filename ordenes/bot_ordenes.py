# bot_ordenes.py
import os
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)
import db_manager as db
from bot_navigation import end_and_return_to_menu
from reporter import send_report, escape, format_user

# Estados de la conversación
(
    ASKING_ORDEN_DESC, ASKING_ORDEN_FOTO, GETTING_ORDEN_FOTO, # Flujo de creación
    LISTING_ORDENES, VIEWING_ORDEN # Flujo de gestión
) = range(5)

# --- Helpers ---
def get_cancel_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancelar", callback_data="cancel_conversation")]])

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query:
        await query.answer("Operación cancelada.")
        await query.edit_message_text("Operación cancelada.")
    else:
        await update.message.reply_text("Operación cancelada.")
    context.user_data.clear()
    return await end_and_return_to_menu(update, context)

# =========================================================================
# FLUJO 1: CREAR ORDEN DE TRABAJO
# =========================================================================
async def start_crear_orden(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data['new_orden'] = {}
    await query.edit_message_text(
        "🆕 *Crear Nueva Orden de Trabajo*\n\n"
        "Por favor, describe la tarea u orden que quieres crear:",
        reply_markup=get_cancel_keyboard(),
        parse_mode='Markdown'
    )
    return ASKING_ORDEN_DESC

async def get_orden_desc(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['new_orden']['descripcion'] = update.message.text
    keyboard = [
        [InlineKeyboardButton("📸 Añadir Foto", callback_data="orden_add_photo")],
        [InlineKeyboardButton("➡️ Omitir Foto", callback_data="orden_skip_photo")]
    ]
    await update.message.reply_text(
        "Descripción guardada. ¿Quieres añadir una foto a la orden?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return ASKING_ORDEN_FOTO

async def ask_orden_foto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    if query.data == 'orden_add_photo':
        await query.edit_message_text("Por favor, envía la foto ahora.", reply_markup=get_cancel_keyboard())
        return GETTING_ORDEN_FOTO
    else: # skip_photo
        context.user_data['new_orden']['foto_path'] = None
        await query.edit_message_text("Guardando orden sin foto...")
        return await save_orden(update, context)

async def get_orden_foto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    photo_file = await update.message.photo[-1].get_file()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    os.makedirs('ordenes_fotos', exist_ok=True)
    file_path = os.path.join('ordenes_fotos', f"orden_{update.effective_user.id}_{timestamp}.jpg")
    await photo_file.download_to_drive(file_path)
    context.user_data['new_orden']['foto_path'] = file_path
    await update.message.reply_text("Foto guardada. Creando orden...")
    return await save_orden(update, context)

async def save_orden(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    data = context.user_data['new_orden']
    
    orden_id = db.create_orden(user.id, data['descripcion'], data.get('foto_path'))
    
    message_source = update.callback_query.message if update.callback_query else update.message
    await message_source.reply_text(
        f"✅ Orden de trabajo #{orden_id} creada con éxito.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Menú Principal", callback_data="back_to_main_menu")]])
    )
    
    report_text = (
        f"🆕 *Nueva Orden de Trabajo Creada*\n\n"
        f"*ID Orden:* `{orden_id}`\n"
        f"*Creada por:* {format_user(user)}\n\n"
        f"*Descripción:*\n_{escape(data['descripcion'])}_"
    )
    await send_report(context, report_text, photo_path=data.get('foto_path'))
    
    context.user_data.clear()
    return ConversationHandler.END

# =========================================================================
# FLUJO 2: GESTIONAR ÓRDENES DE TRABAJO
# =========================================================================
async def start_gestionar_ordenes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    
    ordenes = db.get_ordenes_by_status(['Pendiente'])
    
    if not ordenes:
        await query.edit_message_text(
            "✅ ¡Buen trabajo! No hay órdenes de trabajo pendientes.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Menú Principal", callback_data="back_to_main_menu")]])
        )
        return ConversationHandler.END

    keyboard = []
    for orden in ordenes:
        fecha_str = orden['fecha'].strftime('%d/%m')
        button_text = f"ID:{orden['id']} - Creada por {orden['creador']} ({fecha_str})"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"view_orden_{orden['id']}")])
    
    keyboard.append([InlineKeyboardButton("⬅️ Menú Principal", callback_data="back_to_main_menu")])
    
    await query.edit_message_text(
        "📋 *Órdenes de Trabajo Pendientes*\n\nSelecciona una para ver los detalles y resolverla:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return LISTING_ORDENES

async def view_orden_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    orden_id = int(query.data.split('_')[2])
    
    details = db.get_orden_details(orden_id)
    if not details or details['estado'] != 'Pendiente':
        await query.edit_message_text("Esta orden ya no está disponible o ha sido resuelta.")
        return await start_gestionar_ordenes(update, context)

    texto = (
        f"*Detalle de la Orden \\#{details['id']}*\n\n"
        f"*Creada por:* {escape(details['creador'])}\n"
        f"*Fecha:* {details['fecha_creacion'].strftime('%d/%m/%Y %H:%M')}\n\n"
        f"*Descripción:*\n_{escape(details['descripcion'])}_"
    )
    
    keyboard = [
        [InlineKeyboardButton("✅ Marcar como Realizada", callback_data=f"resolve_orden_{details['id']}")],
        [InlineKeyboardButton("<< Volver a la lista", callback_data="back_to_orden_list")]
    ]
    
    if details['foto_path'] and os.path.exists(details['foto_path']):
        keyboard[0].append(InlineKeyboardButton("Ver Foto", callback_data=f"ver_foto_orden_{details['id']}"))

    await query.edit_message_text(texto, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='MarkdownV2')
    return VIEWING_ORDEN

async def resolve_orden_action(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer("Marcando como realizada...")
    orden_id = int(query.data.split('_')[2])
    user = update.effective_user
    
    db.resolve_orden(orden_id, user.id)
    
    details = db.get_orden_details(orden_id)
    report_text = (
        f"✅ *Orden de Trabajo Realizada*\n\n"
        f"*ID Orden:* `{orden_id}`\n"
        f"*Descripción:* _{escape(details['descripcion'])}_\n\n"
        f"*Realizada por:* {format_user(user)}"
    )
    await send_report(context, report_text)
    
    await query.edit_message_text("¡Orden marcada como realizada! Refrescando lista...")
    return await start_gestionar_ordenes(update, context)

async def ver_foto_orden(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Manejador para mostrar la foto de una orden."""
    query = update.callback_query
    await query.answer()
    try:
        orden_id = int(query.data.split('_')[3])
        details = db.get_orden_details(orden_id)
        if details and details['foto_path'] and os.path.exists(details['foto_path']):
            with open(details['foto_path'], 'rb') as photo_file:
                await context.bot.send_photo(chat_id=query.from_user.id, photo=InputFile(photo_file))
        else:
            await query.message.reply_text("No se encontró la foto para esta orden.")
    except (IndexError, ValueError) as e:
        await query.message.reply_text(f"Error al procesar la solicitud: {e}")

# =========================================================================
# HANDLERS
# =========================================================================
def get_ordenes_handlers():
    crear_orden_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_crear_orden, pattern='^crear_orden$')],
        states={
            ASKING_ORDEN_DESC: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_orden_desc)],
            ASKING_ORDEN_FOTO: [CallbackQueryHandler(ask_orden_foto, pattern='^orden_')],
            GETTING_ORDEN_FOTO: [MessageHandler(filters.PHOTO, get_orden_foto)],
        },
        fallbacks=[CallbackQueryHandler(cancel, pattern='^cancel_conversation$')],
        map_to_parent={ConversationHandler.END: ConversationHandler.END}
    )
    
    gestionar_ordenes_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_gestionar_ordenes, pattern='^gestionar_ordenes$')],
        states={
            LISTING_ORDENES: [CallbackQueryHandler(view_orden_details, pattern='^view_orden_')],
            VIEWING_ORDEN: [
                CallbackQueryHandler(resolve_orden_action, pattern='^resolve_orden_'),
                CallbackQueryHandler(start_gestionar_ordenes, pattern='^back_to_orden_list$')
            ]
        },
        fallbacks=[
            CallbackQueryHandler(end_and_return_to_menu, pattern='^back_to_main_menu$'),
            CallbackQueryHandler(cancel, pattern='^cancel_conversation$')
        ],
        map_to_parent={ConversationHandler.END: ConversationHandler.END}
    )
    
    return [crear_orden_handler, gestionar_ordenes_handler]
