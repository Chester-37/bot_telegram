# almacen/bot_pedidos.py

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
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
from almacen.keyboards import get_cancel_keyboard, get_nav_keyboard

(
    # Estados para la conversación de SOLICITUD de material
    SELECTING_ITEM_TYPE, SELECTING_ITEM, AWAITING_QUANTITY, 
    ASKING_MORE_ITEMS, AWAITING_NOTES,

    # Estados para la conversación de APROBACIÓN de pedidos
    SELECTING_PENDING_PEDIDO, VIEWING_PEDIDO_DETAILS_APPROVAL, AWAITING_REJECTION_NOTES,

    # Estados para la conversación de PREPARACIÓN de pedidos
    SELECTING_APPROVED_PEDIDO, VIEWING_PREPARATION_DETAILS
) = range(10)

ITEMS_PER_PAGE = 5


# --- Helpers ---
def _build_pedido_summary(items_dict: dict) -> str:
    """Construye un texto resumen de los items añadidos al pedido, escapando para MarkdownV2."""
    if not items_dict:
        return ""
    summary = "\n\n*Material añadido al pedido:*\n"
    for item_id, data in items_dict.items():
        summary += f"\\- {data['quantity']} x {escape(data['name'])}\n"
    return summary

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Función de cancelación genérica para todas las conversaciones de este archivo."""
    query = update.callback_query
    if query:
        await query.answer("Operación cancelada.")
        await query.edit_message_text(text="Operación cancelada.")
    else:
        await update.message.reply_text("Operación cancelada.")
    context.user_data.clear()
    return await end_and_return_to_menu(update, context)


# =============================================================================
# FLUJO 1: SOLICITAR MATERIAL (ENCARGADO)
# =============================================================================
async def start_solicitar_material(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia el flujo para solicitar material, preguntando primero por el tipo."""
    query = update.callback_query
    await query.answer()
    
    if 'new_pedido' not in context.user_data:
        context.user_data['new_pedido'] = {'items': {}}

    keyboard = [
        [InlineKeyboardButton("🛠️ Herramientas", callback_data="type_Herramienta")],
        [InlineKeyboardButton("🛡️ EPIs", callback_data="type_EPI")],
        [InlineKeyboardButton("📦 Fungibles", callback_data="type_Fungible")],
        [InlineKeyboardButton("❌ Cancelar Pedido", callback_data="cancel_conversation")]
    ]
    
    summary_text = _build_pedido_summary(context.user_data['new_pedido']['items'])
    # SOLUCIÓN: Se escapa el punto final del mensaje.
    await query.edit_message_text(
        f"📦 *Nuevo Pedido de Material*\n\nSelecciona un tipo de material para añadir\\.{summary_text}",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='MarkdownV2'
    )
    return SELECTING_ITEM_TYPE

async def select_item_type(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Muestra los items del tipo seleccionado de forma paginada."""
    query = update.callback_query
    await query.answer()
    item_type = query.data.split('_')[1]
    context.user_data['current_item_type'] = item_type
    context.user_data['current_page'] = 0
    
    await show_material_page(update, context)
    return SELECTING_ITEM

async def show_material_page(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Función auxiliar para mostrar la página de materiales."""
    query = update.callback_query
    page = context.user_data.get('current_page', 0)
    item_type = context.user_data.get('current_item_type')
    
    materials, total_pages = db.get_almacen_items_paginated(item_type, page, ITEMS_PER_PAGE)

    if not materials and page == 0:
        await query.edit_message_text(f"❌ No hay '{escape(item_type)}' en el inventario\\.", reply_markup=get_cancel_keyboard("Pedido"), parse_mode='MarkdownV2')
        return

    keyboard = []
    for m in materials:
        keyboard.append([InlineKeyboardButton(f"{m['nombre']} (Stock: {m['cantidad']})", callback_data=f"item_{m['id']}_{m['nombre']}")])
    
    pagination_row = []
    if page > 0:
        pagination_row.append(InlineKeyboardButton("⬅️ Ant", callback_data="page_prev"))
    if page < total_pages - 1:
        pagination_row.append(InlineKeyboardButton("Sig ➡️", callback_data="page_next"))
    if pagination_row:
        keyboard.append(pagination_row)

    keyboard.append([InlineKeyboardButton("⬅️ Volver a Tipos", callback_data="back_to_types")])
    
    await query.edit_message_text(
        f"Selecciona un artículo de *{escape(item_type)}* \\(Pág\\. {page + 1}/{total_pages}\\):",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='MarkdownV2'
    )

async def change_material_page(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cambia la página de la lista de materiales."""
    query = update.callback_query
    await query.answer()
    direction = query.data.split('_')[1]
    page = context.user_data.get('current_page', 0)
    context.user_data['current_page'] = page + 1 if direction == 'next' else page - 1
    await show_material_page(update, context)
    return SELECTING_ITEM

async def item_selected(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guarda el item seleccionado y pide la cantidad."""
    query = update.callback_query
    await query.answer()
    _, item_id, item_name = query.data.split('_', 2)
    context.user_data['current_item_id'] = int(item_id)
    context.user_data['current_item_name'] = item_name
    
    await query.edit_message_text(
        f"Has seleccionado: *{escape(item_name)}*\\.\n\n¿Qué cantidad necesitas?",
        parse_mode='MarkdownV2',
        reply_markup=get_cancel_keyboard("Pedido")
    )
    return AWAITING_QUANTITY

async def get_quantity(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guarda la cantidad y pregunta si se quieren añadir más items."""
    try:
        quantity = int(update.message.text)
        if quantity <= 0: raise ValueError
    except ValueError:
        await update.message.reply_text("Por favor, introduce un número positivo.", reply_markup=get_cancel_keyboard("Pedido"))
        return AWAITING_QUANTITY

    item_id = context.user_data['current_item_id']
    context.user_data['new_pedido']['items'][item_id] = {
        'name': context.user_data['current_item_name'],
        'quantity': quantity
    }
    
    summary_text = _build_pedido_summary(context.user_data['new_pedido']['items'])
    keyboard = [
        [InlineKeyboardButton("➕ Añadir más artículos", callback_data="add_more_items")],
        [InlineKeyboardButton("✅ Terminar y enviar pedido", callback_data="finish_pedido")],
    ]
    await update.message.reply_text(
        f"Añadido\\. {summary_text}\n\n¿Qué quieres hacer ahora?",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='MarkdownV2'
    )
    return ASKING_MORE_ITEMS

async def ask_for_notes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Pide notas opcionales para el pedido."""
    query = update.callback_query
    await query.answer()
    
    keyboard = [
        [InlineKeyboardButton("Omitir notas", callback_data="skip_notes")],
        [InlineKeyboardButton("❌ Cancelar Pedido", callback_data="cancel_conversation")]
    ]
    summary_text = _build_pedido_summary(context.user_data['new_pedido']['items'])
    await query.edit_message_text(
        f"Paso Final: Añade notas para el pedido \\(opcional\\)\\.{summary_text}",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='MarkdownV2'
    )
    return AWAITING_NOTES

async def save_pedido(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guarda el pedido completo en la base de datos."""
    query = update.callback_query
    notas = "Sin notas."
    message_source = update.message
    if query:
        message_source = query.message
        await query.answer()
        if query.data != 'skip_notes':
            return AWAITING_NOTES
    else:
        notas = update.message.text
    
    await message_source.reply_text("Guardando pedido...")

    user = update.effective_user
    pedido_data = context.user_data['new_pedido']
    
    if not pedido_data['items']:
        await message_source.reply_text("❌ No has añadido ningún artículo. Pedido cancelado.", reply_markup=get_nav_keyboard())
        return await end_and_return_to_menu(update, context)

    pedido_id = db.create_pedido(user.id, notas)
    for item_id, details in pedido_data['items'].items():
        db.add_item_to_pedido(pedido_id, item_id, details['quantity'])

    await message_source.reply_text(f"✅ Pedido #{pedido_id} enviado para aprobación.", reply_markup=get_nav_keyboard())
    
    # Notificaciones
    summary_text = _build_pedido_summary(pedido_data['items'])
    report_text = (
        f"📦 *Nuevo Pedido de Material*\n\n"
        f"*ID Pedido:* `{pedido_id}`\n"
        f"*Solicitante:* {format_user(user)}\n"
        f"{summary_text}\n"
        f"*Notas:* {escape(notas)}"
    )
    await send_report(context, report_text)
    
    context.user_data.clear()
    return ConversationHandler.END


# =============================================================================
# FLUJO 2: APROBACIÓN DE PEDIDOS (TÉCNICO)
# =============================================================================
async def show_pending_requests(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    pedidos = db.get_pedidos_by_estado('Pendiente Aprobacion')
    if not pedidos:
        await query.edit_message_text("✅ No hay pedidos pendientes de aprobación.", reply_markup=get_nav_keyboard())
        return ConversationHandler.END

    keyboard = [[InlineKeyboardButton(f"ID:{p['id']} de {p['solicitante']} ({p['fecha']})", callback_data=f"view_pedido_{p['id']}")] for p in pedidos]
    keyboard.append([InlineKeyboardButton("⬅️ Menú Principal", callback_data="back_to_main_menu")])
    await query.edit_message_text("Selecciona un pedido para revisar:", reply_markup=InlineKeyboardMarkup(keyboard))
    return SELECTING_PENDING_PEDIDO

async def view_pedido_details_for_approval(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    pedido_id = int(query.data.split('_')[2])
    context.user_data['current_pedido_id'] = pedido_id
    details = db.get_pedido_details(pedido_id)
    if not details:
        await query.edit_message_text("❌ Error: No se encontró el pedido.", reply_markup=get_nav_keyboard())
        return ConversationHandler.END

    texto_items = "\n".join([f"• {escape(item['nombre'])} `(Cant: {item['cantidad_solicitada']})`" for item in details['items']])
    
    texto = (f"📦 *Detalles del Pedido \\#{details['id']}*\n"
             f"👤 *Solicitante:* {escape(details['solicitante'])}\n"
             f"📝 *Notas:* {escape(details['notas_solicitud'] or 'Ninguna')}\n\n"
             f"*Artículos Solicitados:*\n{texto_items}")

    keyboard = [
        [InlineKeyboardButton("✅ Aprobar", callback_data=f"act_approve")],
        [InlineKeyboardButton("❌ Rechazar", callback_data=f"act_reject")],
        [InlineKeyboardButton("<< Volver a la lista", callback_data="back_to_list_approval")]
    ]
    await query.edit_message_text(texto, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='MarkdownV2')
    return VIEWING_PEDIDO_DETAILS_APPROVAL

async def approve_pedido(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    pedido_id = context.user_data['current_pedido_id']
    # MEJOR PRÁCTICA: Obtener el usuario desde la query en un CallbackQueryHandler
    user = query.from_user
    
    db.update_pedido_status(pedido_id, 'Aprobado', user.id, "Aprobado sin cambios.")
    await query.edit_message_text(f"✅ Pedido #{pedido_id} aprobado.", reply_markup=get_nav_keyboard())
    
    details = db.get_pedido_details(pedido_id)
    if not details:
        context.user_data.clear()
        return ConversationHandler.END

    await context.bot.send_message(details['solicitante_id'], f"✅ Tu pedido de material #{pedido_id} ha sido *APROBADO*.")
    for almacen_user in db.get_users_by_role('Almacen'):
        await context.bot.send_message(almacen_user['id'], f"📦 El pedido #{pedido_id} ha sido APROBADO. Por favor, prepararlo para su recogida.")

    report_text = (
        f"✅ *Reporte: Pedido de Material Aprobado* ✅\n\n"
        f"*ID Pedido:* `{pedido_id}`\n"
        f"*Aprobado por:* {format_user(user)}"
    )
    await send_report(context, report_text)
    
    context.user_data.clear()
    return ConversationHandler.END

async def ask_rejection_notes(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Por favor, escribe el motivo del rechazo:", reply_markup=get_cancel_keyboard("Rechazo"))
    return AWAITING_REJECTION_NOTES

async def reject_pedido(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    rejection_notes = update.message.text
    pedido_id = context.user_data['current_pedido_id']
    user = update.effective_user
    
    db.update_pedido_status(pedido_id, 'Rechazado', user.id, rejection_notes)
    await update.message.reply_text(f"❌ Pedido #{pedido_id} rechazado.", reply_markup=get_nav_keyboard())
    
    details = db.get_pedido_details(pedido_id)
    if not details:
        context.user_data.clear()
        return ConversationHandler.END

    await context.bot.send_message(details['solicitante_id'], f"❌ Tu pedido de material #{pedido_id} ha sido *RECHAZADO*.\n*Motivo:* {rejection_notes}")

    report_text = (
        f"❌ *Reporte: Pedido de Material Rechazado* ❌\n\n"
        f"*ID Pedido:* `{pedido_id}`\n"
        f"*Rechazado por:* {format_user(user)}\n"
        f"*Motivo:* {escape(rejection_notes)}"
    )
    await send_report(context, report_text)

    context.user_data.clear()
    return ConversationHandler.END


# =============================================================================
# FLUJO 3: PREPARACIÓN DE PEDIDOS (ALMACÉN)
# =============================================================================
async def show_approved_requests(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    pedidos = db.get_pedidos_by_estado('Aprobado')
    if not pedidos:
        await query.edit_message_text("✅ No hay pedidos pendientes de preparar.", reply_markup=get_nav_keyboard())
        return ConversationHandler.END

    keyboard = [[InlineKeyboardButton(f"ID:{p['id']} de {p['solicitante']}", callback_data=f"prep_view_{p['id']}")] for p in pedidos]
    keyboard.append([InlineKeyboardButton("⬅️ Menú Principal", callback_data="back_to_main_menu")])
    await query.edit_message_text("Selecciona un pedido para preparar:", reply_markup=InlineKeyboardMarkup(keyboard))
    return SELECTING_APPROVED_PEDIDO

async def view_preparation_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    pedido_id = int(query.data.split('_')[2])
    context.user_data['current_pedido_id'] = pedido_id
    details = db.get_pedido_details(pedido_id)
    if not details:
        await query.edit_message_text("❌ Error: No se encontró el pedido.", reply_markup=get_nav_keyboard())
        return ConversationHandler.END

    texto_items = "\n".join([f"• {escape(item['nombre'])} `(Cant: {item['cantidad_solicitada']})`" for item in details['items']])
    
    texto = (f"📦 *Preparar Pedido \\#{details['id']}*\n"
             f"👤 *Solicitante:* {escape(details['solicitante'])}\n\n"
             f"*Artículos a Preparar:*\n{texto_items}")
             
    keyboard = [
        [InlineKeyboardButton("✅ Marcar como Listo para Recoger", callback_data=f"prep_ready")],
        [InlineKeyboardButton("<< Volver a la lista", callback_data="back_to_prep_list")]
    ]
    await query.edit_message_text(texto, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='MarkdownV2')
    return VIEWING_PREPARATION_DETAILS

async def mark_as_ready(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    pedido_id = context.user_data['current_pedido_id']
    user = query.from_user
    db.update_pedido_status(pedido_id, 'Listo para Recoger', user.id)
    await query.edit_message_text(f"✅ Pedido #{pedido_id} marcado como 'Listo para Recoger'.", reply_markup=get_nav_keyboard())
    
    details = db.get_pedido_details(pedido_id)
    if not details:
        context.user_data.clear()
        return ConversationHandler.END

    await context.bot.send_message(details['solicitante_id'], f"👍 Tu pedido de material #{pedido_id} está *listo para ser recogido* en el almacén.")

    report_text = (
        f"🚚 *Reporte: Pedido Preparado* 🚚\n\n"
        f"*ID Pedido:* `{pedido_id}`\n"
        f"*Preparado por:* {format_user(user)}"
    )
    await send_report(context, report_text)

    context.user_data.clear()
    return ConversationHandler.END


# =============================================================================
# HANDLERS DE CONVERSACIÓN
# =============================================================================
def get_solicitar_material_handler():
    """Crea y devuelve el ConversationHandler para solicitar material."""
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(start_solicitar_material, pattern='^solicitar_material$')],
        states={
            SELECTING_ITEM_TYPE: [CallbackQueryHandler(select_item_type, pattern='^type_')],
            SELECTING_ITEM: [
                CallbackQueryHandler(change_material_page, pattern='^page_'),
                CallbackQueryHandler(item_selected, pattern='^item_'),
                CallbackQueryHandler(start_solicitar_material, pattern='^back_to_types$')
            ],
            AWAITING_QUANTITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_quantity)],
            ASKING_MORE_ITEMS: [
                CallbackQueryHandler(start_solicitar_material, pattern='^add_more_items$'),
                CallbackQueryHandler(ask_for_notes, pattern='^finish_pedido$'),
            ],
            AWAITING_NOTES: [
                CallbackQueryHandler(save_pedido, pattern='^skip_notes$'),
                MessageHandler(filters.TEXT & ~filters.COMMAND, save_pedido),
            ],
        },
        fallbacks=[CallbackQueryHandler(cancel, pattern='^cancel_conversation$')],
    )

def get_pedidos_approval_handler():
    """Crea y devuelve el ConversationHandler para aprobar pedidos."""
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(show_pending_requests, pattern='^aprobar_pedidos$')],
        states={
            SELECTING_PENDING_PEDIDO: [CallbackQueryHandler(view_pedido_details_for_approval, pattern='^view_pedido_')],
            VIEWING_PEDIDO_DETAILS_APPROVAL: [
                CallbackQueryHandler(approve_pedido, pattern='^act_approve$'),
                CallbackQueryHandler(ask_rejection_notes, pattern='^act_reject$'),
                CallbackQueryHandler(show_pending_requests, pattern='^back_to_list_approval$'),
            ],
            AWAITING_REJECTION_NOTES: [MessageHandler(filters.TEXT & ~filters.COMMAND, reject_pedido)],
        },
        fallbacks=[CallbackQueryHandler(cancel, pattern='^cancel_conversation$')],
    )

def get_pedidos_preparation_handler():
    """Crea y devuelve el ConversationHandler para preparar pedidos."""
    return ConversationHandler(
        entry_points=[CallbackQueryHandler(show_approved_requests, pattern='^preparar_pedidos$')],
        states={
            SELECTING_APPROVED_PEDIDO: [CallbackQueryHandler(view_preparation_details, pattern='^prep_view_')],
            VIEWING_PREPARATION_DETAILS: [
                CallbackQueryHandler(mark_as_ready, pattern='^prep_ready$'),
                CallbackQueryHandler(show_approved_requests, pattern='^back_to_prep_list$')
            ]
        },
        fallbacks=[CallbackQueryHandler(cancel, pattern='^cancel_conversation$')],
    )
