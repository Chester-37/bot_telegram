# prevencion/bot_prevencion.py
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

# Se definen todos los estados necesarios para todos los flujos
(
    # Flujo de creación
    SELECTING_PREV_UBICACION, GET_DESCRIPCION, GET_FOTO,
    # Flujo de comunicado
    GET_COMUNICADO_TEXT,
    # Flujo de comentarios
    AWAITING_PREV_COMMENT,
    # Flujo de consulta de "Mis Incidencias"
    LISTING_MY_PREV_INCIDENCIAS, VIEWING_MY_PREV_INCIDENCIA
) = range(7)
# --- FIN DE LA CORRECCIÓN ---

# --- Helpers ---
def get_cancel_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancelar", callback_data="cancel_conversation")]])

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Función de cancelación genérica para conversaciones."""
    query = update.callback_query
    if query:
        await query.answer()
        await query.edit_message_text("Operación cancelada.")
    else:
        await update.message.reply_text("Operación cancelada.")
    context.user_data.clear()
    # Usamos la función estándar para asegurar una salida limpia
    return await end_and_return_to_menu(update, context)

# =============================================================================
# FLUJO 1: REPORTAR NUEVA INCIDENCIA DE PREVENCIÓN
# =============================================================================
async def start_reporte_prevencion(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Inicia el flujo de reporte pidiendo el primer nivel de ubicación."""
    query = update.callback_query
    await query.answer()
    
    # --- INICIO DE LA CORRECCIÓN ---
    # 1. Obtenemos los tipos de ubicación de la BD
    hierarchy = db.get_distinct_ubicacion_tipos()
    
    # 2. Definimos el orden deseado y lo aplicamos
    order_preference = ['Edificio', 'Planta', 'Zona', 'Trabajo']
    hierarchy.sort(key=lambda tipo: order_preference.index(tipo) if tipo in order_preference else len(order_preference))
    # --- FIN DE LA CORRECCIÓN ---

    if not hierarchy:
        await query.edit_message_text(
            "❌ Error: No hay tipos de ubicación configurados. No se puede reportar.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Menú Principal", callback_data="back_to_main_menu")]])
        )
        return ConversationHandler.END

    context.user_data.clear()
    context.user_data['new_prev_inc'] = {}
    context.user_data['prev_location_hierarchy'] = hierarchy
    context.user_data['prev_location_parts'] = []

    first_level = hierarchy[0]
    return await ask_for_location_level(update, context, level_name=first_level)

async def ask_for_location_level(update: Update, context: ContextTypes.DEFAULT_TYPE, level_name: str) -> int:
    """Muestra los botones para un nivel de ubicación específico."""
    query = update.callback_query
    
    options = db.get_ubicaciones_by_tipo(level_name)
    
    keyboard = []
    for option in options:
        # --- INICIO DE LA CORRECCIÓN ---
        # Se simplifica el callback_data para evitar el error de split
        callback_data = f"prev_loc_{level_name}_{option['nombre']}"
        # --- FIN DE LA CORRECCIÓN ---
        keyboard.append([InlineKeyboardButton(option['nombre'], callback_data=callback_data)])
    
    keyboard.append([InlineKeyboardButton("❌ Cancelar", callback_data="cancel_conversation")])
    
    selected_parts = context.user_data.get('prev_location_parts', [])
    summary = " / ".join(selected_parts) if selected_parts else "Ninguna"
    
    message_text = (
        f"📝 **Reportar Incidencia de Prevención**\n"
        f"Ubicación actual: `{escape(summary)}`\n\n"
        f"Paso 1: Selecciona un/a *{escape(level_name)}*:"
    )
    
    if query:
        await query.edit_message_text(
            text=message_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='MarkdownV2'
        )
    else:
        await update.message.reply_text(
            text=message_text,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode='MarkdownV2'
        )

    return SELECTING_PREV_UBICACION

async def process_location_selection(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Procesa la selección de un botón de ubicación y avanza al siguiente nivel o al siguiente paso."""
    query = update.callback_query
    await query.answer()
    
    _, _, level, value = query.data.split('_', 3)
    
    context.user_data['prev_location_parts'].append(value)
    
    hierarchy = context.user_data['prev_location_hierarchy']
    current_index = hierarchy.index(level)
    
    if current_index + 1 < len(hierarchy):
        next_level = hierarchy[current_index + 1]
        return await ask_for_location_level(update, context, level_name=next_level)
    else:
        final_location = " / ".join(context.user_data['prev_location_parts'])
        context.user_data['new_prev_inc']['ubicacion'] = final_location
        
        await query.edit_message_text(
            f"Ubicación seleccionada: `{escape(final_location)}`\n\n"
            "Paso 2: Describe la incidencia encontrada\\.",
            reply_markup=get_cancel_keyboard(),
            parse_mode='MarkdownV2'
        )
        return GET_DESCRIPCION

async def get_descripcion(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['new_prev_inc']['descripcion'] = update.message.text
    keyboard = [
        [InlineKeyboardButton("Omitir Foto", callback_data="skip_photo")],
        [InlineKeyboardButton("❌ Cancelar", callback_data="cancel_conversation")]
    ]
    await update.message.reply_text(
        "Paso 3: Envía una foto de la incidencia o pulsa 'Omitir Foto'.",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return GET_FOTO

async def get_foto(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Maneja tanto la recepción de una foto como la omisión de la misma."""
    query = update.callback_query
    
    if query and query.data == 'skip_photo':
        await query.answer()
        context.user_data['new_prev_inc']['foto_path'] = None
        await query.edit_message_text("✅ Foto omitida. Guardando incidencia...")
        return await save_incidencia(update, context)

    elif update.message and update.message.photo:
        photo_file = await update.message.photo[-1].get_file()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        os.makedirs('prevencion_fotos', exist_ok=True)
        file_path = os.path.join('prevencion_fotos', f"prevencion_{update.effective_user.id}_{timestamp}.jpg")
        await photo_file.download_to_drive(file_path)
        context.user_data['new_prev_inc']['foto_path'] = file_path
        await update.message.reply_text("✅ Foto recibida. Guardando incidencia...")
        return await save_incidencia(update, context)
        
    await update.message.reply_text("Por favor, envía una foto o pulsa el botón 'Omitir Foto'.")
    return GET_FOTO

async def save_incidencia(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Guarda la incidencia y envía la notificación."""
    user = update.effective_user
    data = context.user_data['new_prev_inc']
    
    incidencia_id = db.create_prevencion_incidencia(
        reporta_id=user.id,
        ubicacion=data['ubicacion'],
        descripcion=data['descripcion'],
        foto_path=data.get('foto_path')
    )

    message_source = update.callback_query.message if update.callback_query else update.message

    await message_source.reply_text(
        f"✅ Incidencia de prevención #{incidencia_id} registrada correctamente.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Menú Principal", callback_data="back_to_main_menu")]])
    )

    report_text = (
        f"🕵️‍♂️ *Nueva Incidencia de Prevención* 🕵️‍♂️\n\n"
        f"*ID:* `{incidencia_id}`\n"
        f"*Reportada por:* {format_user(user)}\n"
        f"*Ubicación:* {escape(data['ubicacion'])}\n"
        f"*Descripción:* _{escape(data['descripcion'])}_"
    )
    # Se envía la foto al grupo si existe
    await send_report(context, report_text, photo_path=data.get('foto_path'))
    
    context.user_data.clear()
    return ConversationHandler.END

# =============================================================================
# FLUJO 2: GESTIONAR INCIDENCIAS DE PREVENCIÓN (PARA ENCARGADOS/TÉCNICOS)
# =============================================================================
async def menu_ver_incidencias_prevencion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra el menú para ver incidencias abiertas o en disputa."""
    query = update.callback_query
    await query.answer()
    keyboard = [
        [InlineKeyboardButton("🚨 Ver Abiertas / En Disputa", callback_data="prev_view_Abierta")],
        [InlineKeyboardButton("✅ Ver Cerradas", callback_data="prev_view_Cerrada")],
        [InlineKeyboardButton("⬅️ Menú Principal", callback_data="back_to_main_menu")]
    ]
    await query.edit_message_text(
        "**Gestión de Incidencias de Prevención**\n\nSelecciona qué incidencias deseas ver:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )

async def listar_incidencias_prevencion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Muestra una lista de incidencias según el estado seleccionado."""
    query = update.callback_query
    await query.answer()
    estado = query.data.split('_')[2]
    
    estados_a_buscar = ['Abierta', 'En Disputa'] if estado == 'Abierta' else ['Cerrada']
    
    incidencias = db.get_prevencion_incidencias_by_estado(estados_a_buscar)

    if not incidencias:
        await query.edit_message_text(
            f"✅ No hay incidencias con estado '{'Abiertas o En Disputa' if estado == 'Abierta' else 'Cerradas'}'.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Menú Principal", callback_data="back_to_main_menu")]])
        )
        return

    await query.edit_message_text(f"Buscando incidencias...")
    for inc in incidencias:
        texto = (
            f"🕵️‍♂️ *Incidencia de Prevención \\#{inc['id']}*\n"
            f"*Estado:* `{inc['estado']}`\n"
            f"*Ubicación:* {escape(inc['ubicacion'])}\n"
            f"*Reportada por:* {escape(inc['reporta_nombre'])} el {escape(inc['fecha'])}\n"
            f"*Descripción:* _{escape(inc['descripcion'])}_"
        )
        keyboard = []
        row = []
        if inc['estado'] != 'Cerrada':
            row.append(InlineKeyboardButton("✅ Cerrar", callback_data=f"prev_close_{inc['id']}"))
            row.append(InlineKeyboardButton("💬 Comentar", callback_data=f"prev_comment_{inc['id']}"))
        if inc['has_foto']:
            row.append(InlineKeyboardButton("📸 Ver Foto", callback_data=f"prev_photo_{inc['id']}"))
        if row:
            keyboard.append(row)
            
        await query.message.reply_text(texto, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='MarkdownV2')
    
    await query.message.reply_text(
        "Fin de la lista.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Menú Principal", callback_data="back_to_main_menu")]])
    )

async def cerrar_incidencia_prevencion(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    incidencia_id = int(query.data.split('_')[2])
    db.close_prevencion_incidencia(incidencia_id, update.effective_user.id)
    
    await query.edit_message_text(f"✅ Incidencia #{incidencia_id} marcada como **Cerrada**.", parse_mode='Markdown')

    report_text = (
        f"✅ *Incidencia de Prevención Cerrada*\n\n"
        f"*ID:* `{incidencia_id}`\n"
        f"*Cerrada por:* {format_user(update.effective_user)}"
    )
    await send_report(context, report_text)

async def start_comment_prevencion(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    incidencia_id = int(query.data.split('_')[2])
    context.user_data['prev_comment_id'] = incidencia_id
    await query.edit_message_text(
        "💬 Por favor, escribe tu comentario o consulta sobre la incidencia.",
        reply_markup=get_cancel_keyboard()
    )
    return AWAITING_PREV_COMMENT

async def save_comment_prevencion(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    incidencia_id = context.user_data['prev_comment_id']
    comentario = update.message.text
    
    db.add_prevencion_comentario(incidencia_id, user.id, comentario)
    
    await update.message.reply_text(
        "✅ Tu comentario ha sido añadido y la incidencia marcada como 'En Disputa'.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Menú Principal", callback_data="back_to_main_menu")]])
    )

    details = db.get_prevencion_incidencia_details(incidencia_id)
    if details and details['reporta_id']:
        notification_text = (
            f"💬 *Nuevo comentario en tu incidencia de prevención \\#{incidencia_id}*\n\n"
            f"*{format_user(user)}* comentó:\n"
            f"_{escape(comentario)}_"
        )
        try:
            await context.bot.send_message(
                chat_id=details['reporta_id'],
                text=notification_text,
                parse_mode='MarkdownV2'
            )
        except Exception as e:
            print(f"No se pudo notificar al usuario de prevención {details['reporta_id']}: {e}")

    context.user_data.clear()
    return ConversationHandler.END

# =============================================================================
# FLUJO 3: ENVIAR COMUNICADO GENERAL
# =============================================================================
async def start_comunicado(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    query = update.callback_query
    await query.answer()
    await query.edit_message_text(
        "📢 **Enviar Comunicado General**\n\nEscribe el mensaje que quieres enviar al grupo principal.",
        reply_markup=get_cancel_keyboard(),
        parse_mode='Markdown'
    )
    return GET_COMUNICADO_TEXT

async def send_comunicado(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user = update.effective_user
    mensaje = update.message.text
    
    report_text = (
        f"📢 *Comunicado de Prevención*\n\n"
        f"De: {format_user(user)}\n\n"
        f"_{escape(mensaje)}_"
    )
    
    await send_report(context, report_text)
    
    await update.message.reply_text(
        "✅ Comunicado enviado con éxito.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Menú Principal", callback_data="back_to_main_menu")]])
    )
    return ConversationHandler.END

# --- INICIO DE LA MODIFICACIÓN ---
# =============================================================================
# FLUJO 4: CONSULTAR MIS INCIDENCIAS REPORTADAS
# =============================================================================
async def start_mis_incidencias(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Muestra al usuario de Prevención una lista de las incidencias que ha reportado."""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    incidencias = db.get_prevencion_incidencias_by_reporter(user_id)
    
    if not incidencias:
        await query.edit_message_text(
            "✅ No has reportado ninguna incidencia de prevención.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Menú Principal", callback_data="back_to_main_menu")]])
        )
        return ConversationHandler.END

    keyboard = []
    for inc in incidencias:
        status_emoji = {'Abierta': '🔴', 'En Disputa': '🟡', 'Cerrada': '✅'}.get(inc['estado'], '❔')
        desc_corta = (inc['descripcion'][:30] + '...') if len(inc['descripcion']) > 30 else inc['descripcion']
        button_text = f"{status_emoji} ID:{inc['id']} - {desc_corta}"
        keyboard.append([InlineKeyboardButton(button_text, callback_data=f"view_my_prev_{inc['id']}")])
    
    keyboard.append([InlineKeyboardButton("⬅️ Menú Principal", callback_data="back_to_main_menu")])
    
    await query.edit_message_text(
        "📋 *Mis Incidencias Reportadas*\n\nSelecciona una para ver su estado y detalles:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    return LISTING_MY_PREV_INCIDENCIAS

async def view_my_prev_incidencia_details(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Muestra los detalles de una incidencia de prevención seleccionada."""
    query = update.callback_query
    await query.answer()
    incidencia_id = int(query.data.split('_')[3])
    
    details = db.get_prevencion_incidencia_details(incidencia_id)
    if not details:
        await query.edit_message_text("❌ Error: No se encontró la incidencia.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("<< Volver a la lista", callback_data="back_to_my_list")]]))
        return LISTING_MY_PREV_INCIDENCIAS

    texto = (
        f"🕵️‍♂️ *Detalle de Incidencia \\#{details['id']}*\n\n"
        f"*Estado:* `{escape(details['estado'])}`\n"
        f"*Fecha de Reporte:* {details['fecha_creacion'].strftime('%d/%m/%Y %H:%M')}\n"
        f"*Ubicación:* {escape(details['ubicacion'])}\n\n"
        f"*Descripción:*\n_{escape(details['descripcion'])}_\n"
    )
    
    if details['estado'] == 'Cerrada' and details['resolutor']:
        texto += f"\n*Cerrada por:* {escape(details['resolutor'])} el {details['fecha_cierre'].strftime('%d/%m/%Y')}"

    keyboard = [[InlineKeyboardButton("<< Volver a la lista", callback_data="back_to_my_list")]]
    if details['foto_path']:
        # La función para ver la foto no está en una conversación, por lo que no necesita un handler especial aquí
        keyboard[0].append(InlineKeyboardButton("📸 Ver Foto", callback_data=f"prev_photo_{details['id']}"))

    await query.edit_message_text(texto, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode='MarkdownV2')
    return VIEWING_MY_PREV_INCIDENCIA

# =============================================================================
# HANDLERS DE LA CONVERSACIÓN
# =============================================================================
def get_prevencion_handlers():
    report_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_reporte_prevencion, pattern='^prevencion_reportar$')],
        states={
            SELECTING_PREV_UBICACION: [
                # --- INICIO DE LA CORRECCIÓN ---
                # El patrón ahora coincide con el nuevo callback_data "prev_loc_..."
                CallbackQueryHandler(process_location_selection, pattern='^prev_loc_')
                # --- FIN DE LA CORRECCIÓN ---
            ],
            GET_DESCRIPCION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_descripcion)],
            GET_FOTO: [
                MessageHandler(filters.PHOTO, get_foto),
                CallbackQueryHandler(get_foto, pattern='^skip_photo$')
            ],
        },
        fallbacks=[CallbackQueryHandler(cancel, pattern='^cancel_conversation$')],
        map_to_parent={ConversationHandler.END: ConversationHandler.END},
        allow_reentry=True
    )

    comunicado_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_comunicado, pattern='^prevencion_comunicado$')],
        states={
            GET_COMUNICADO_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, send_comunicado)]
        },
        fallbacks=[CallbackQueryHandler(cancel, pattern='^cancel_conversation$')],
        map_to_parent={ConversationHandler.END: ConversationHandler.END}
    )
    
    comment_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_comment_prevencion, pattern='^prev_comment_')],
        states={
            AWAITING_PREV_COMMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_comment_prevencion)]
        },
        fallbacks=[CallbackQueryHandler(cancel, pattern='^cancel_conversation$')],
        map_to_parent={ConversationHandler.END: ConversationHandler.END}
    )

    mis_incidencias_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(start_mis_incidencias, pattern='^prevencion_mis_incidencias$')],
        states={
            LISTING_MY_PREV_INCIDENCIAS: [CallbackQueryHandler(view_my_prev_incidencia_details, pattern='^view_my_prev_')],
            VIEWING_MY_PREV_INCIDENCIA: [CallbackQueryHandler(start_mis_incidencias, pattern='^back_to_my_list$')]
        },
        fallbacks=[
            CallbackQueryHandler(end_and_return_to_menu, pattern='^back_to_main_menu$'),
            CallbackQueryHandler(cancel, pattern='^cancel_conversation$')
        ],
        map_to_parent={ConversationHandler.END: ConversationHandler.END}
    )

    return [report_handler, comunicado_handler, comment_handler, mis_incidencias_handler]
