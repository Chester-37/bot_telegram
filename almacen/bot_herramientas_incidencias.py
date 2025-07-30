# almacen/bot_herramientas_incidencias.py
import os
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
)
import db_manager as db
from bot_navigation import end_and_return_to_menu, start
from reporter import send_report, escape, format_user
from almacen.keyboards import get_cancel_keyboard, get_nav_keyboard

SELECTING_TOOL, AWAITING_DESCRIPTION, AWAITING_PHOTO = range(20, 23)
ITEMS_PER_PAGE = 5

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query:
        await query.answer("Operación cancelada.")
        await query.edit_message_text("Operación cancelada.")
    else:
        await update.message.reply_text("Operación cancelada.")
    context.user_data.clear()
    await start(update, context)
    return ConversationHandler.END

# --- Flujo de la Conversación ---
async def start_tool_incidencia(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    context.user_data['current_page'] = 0
    await show_tool_page(update, context)
    return SELECTING_TOOL

async def show_tool_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    page = context.user_data.get('current_page', 0)
    tools, total_pages = db.get_almacen_items_paginated('Herramienta', page, ITEMS_PER_PAGE)

    if not tools and page == 0:
        await query.edit_message_text("❌ No hay herramientas en el inventario para reportar.", reply_markup=get_nav_keyboard())
        return ConversationHandler.END

    keyboard = [[
        InlineKeyboardButton(tool['nombre'], callback_data=f"tool_{tool['id']}_{tool['nombre']}")
    ] for tool in tools]
    pagination_buttons = []
    if page > 0:
        pagination_buttons.append(InlineKeyboardButton("⬅️ Anterior", callback_data="page_prev"))
    if page < total_pages - 1:
        pagination_buttons.append(InlineKeyboardButton("Siguiente ➡️", callback_data="page_next"))
    if pagination_buttons:
        keyboard.append(pagination_buttons)
    keyboard.append([InlineKeyboardButton("❌ Cancelar", callback_data="cancel_conversation")])
    message_text = f"Selecciona la herramienta averiada (Página {page + 1}/{total_pages}):"
    await query.edit_message_text(text=message_text, reply_markup=InlineKeyboardMarkup(keyboard))

async def change_page(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    page_direction = query.data.split('_')[1]
    current_page = context.user_data.get('current_page', 0)
    context.user_data['current_page'] = current_page + 1 if page_direction == 'next' else current_page - 1
    await show_tool_page(update, context)
    return SELECTING_TOOL

async def tool_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    _, item_id, item_name = query.data.split('_', 2)
    context.user_data['new_incidence'] = {'item_id': int(item_id), 'item_name': item_name}
    await query.edit_message_text(f"Herramienta seleccionada: *{escape(item_name)}*\\.\n\nAhora, describe la avería\\.", parse_mode='MarkdownV2', reply_markup=get_cancel_keyboard())
    return AWAITING_DESCRIPTION

async def get_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['new_incidence']['descripcion'] = update.message.text
    keyboard = [
        [InlineKeyboardButton("Añadir Foto", callback_data='photo_add')],
        [InlineKeyboardButton("Sin Foto", callback_data='photo_skip')],
        [InlineKeyboardButton("❌ Cancelar", callback_data="cancel_conversation")]
    ]
    await update.message.reply_text("¿Quieres añadir una foto de la avería?", reply_markup=InlineKeyboardMarkup(keyboard))
    return AWAITING_PHOTO

async def get_photo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    if query:
        await query.answer()
        if query.data == 'photo_add':
            await query.edit_message_text("Por favor, envía la foto ahora.", reply_markup=get_cancel_keyboard())
            return AWAITING_PHOTO
        else: # skip photo
            context.user_data['new_incidence']['foto_path'] = None
            await query.edit_message_text("Registrando incidencia...")
            await save_and_notify(update, context)
            return ConversationHandler.END
    else: # foto enviada
        photo_file = await update.message.photo[-1].get_file()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"incidencia_tool_{update.effective_user.id}_{timestamp}.jpg"
        os.makedirs('incidencias_fotos', exist_ok=True)
        file_path = os.path.join('incidencias_fotos', file_name)
        await photo_file.download_to_drive(file_path)
        context.user_data['new_incidence']['foto_path'] = file_path
        await update.message.reply_text("Foto recibida. Registrando incidencia...")
        await save_and_notify(update, context)
        return ConversationHandler.END

async def save_and_notify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    data = context.user_data['new_incidence']
    message_source = update.callback_query.message if update.callback_query else update.message

    incidencia_id = db.create_tool_incidencia(user.id, data['item_id'], data['descripcion'], data.get('foto_path'))
    await message_source.reply_text(f"✅ Incidencia de herramienta registrada con ID #{incidencia_id}.", reply_markup=get_nav_keyboard())

    report_text = (
        f"🔩 *Reporte: Incidencia de Herramienta* 🔩\n\n"
        f"*ID Incidencia:* `{incidencia_id}`\n"
        f"*Reportada por:* {format_user(user)}\n"
        f"*Herramienta:* {escape(data['item_name'])}\n\n"
        f"*Descripción:*\n_{escape(data['descripcion'])}_"
    )
    await send_report(context, report_text)

    tecnicos = db.get_users_by_role('Tecnico')
    texto_notificacion = f"🔩 *Avería en Herramienta:* {escape(data['item_name'])} \\(ID: {incidencia_id}\\)"
    keyboard = [[InlineKeyboardButton("Ver y Resolver", callback_data=f'resolve_{incidencia_id}')]]
    if data.get('foto_path'):
        keyboard[0].append(InlineKeyboardButton("Ver Foto", callback_data=f'ver_foto_incidencia_{incidencia_id}'))
    for tecnico in tecnicos:
        await context.bot.send_message(tecnico['id'], texto_notificacion, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='MarkdownV2')
    context.user_data.clear()

def get_tool_incidencia_handler():
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(start_tool_incidencia, pattern='^crear_incidencia$')],
        states={
            SELECTING_TOOL: [
                CallbackQueryHandler(change_page, pattern='^page_'),
                CallbackQueryHandler(tool_selected, pattern='^tool_'),
            },
            AWAITING_DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_description)],
            AWAITING_PHOTO: [
                CallbackQueryHandler(get_photo, pattern='^photo_'),
                MessageHandler(filters.PHOTO, get_photo)
            ],
        },
        fallbacks=[CallbackQueryHandler(cancel, pattern='^cancel_conversation$')],
        map_to_parent={ConversationHandler.END: ConversationHandler.END}
    )
            ],
        },
        fallbacks=[CallbackQueryHandler(cancel, pattern='^cancel_conversation$')],
        map_to_parent={ConversationHandler.END: ConversationHandler.END}
    )
                CallbackQueryHandler(get_photo, pattern='^photo_'),
                MessageHandler(filters.PHOTO, get_photo)
            ],
        },
        fallbacks=[CallbackQueryHandler(cancel, pattern='^cancel_conversation$')],
        map_to_parent={ConversationHandler.END: ConversationHandler.END}
    )
